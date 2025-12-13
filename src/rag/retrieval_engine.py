"""검색 엔진 구현 (Enhanced with Hybrid Search & Reranking & Simulated GraphRAG)"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json  # noqa: F401
import asyncio
import re

# 선택적 import (임베딩/재순위화 모델)
try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.cross_encoder import CrossEncoder
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    CrossEncoder = None  # type: ignore

# Pinecone import
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None  # type: ignore

# Voyage AI import for embeddings
try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    voyageai = None  # type: ignore

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """검색 엔진 (Hybrid + Reranking + GraphRAG Extension)"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("RetrievalEngine")

        # 검색 설정
        self.vector_weight = self.config.get('vector_weight', 0.5) # Balanced default
        self.keyword_weight = self.config.get('keyword_weight', 0.5)
        self.max_results = self.config.get('max_results', 20) # Fetch more for reranking
        self.rerank_top_k = self.config.get('rerank_top_k', 5) # Final Top K
        self.similarity_threshold = self.config.get('similarity_threshold', 0.5)

        # GraphRAG 설정
        self.graph_enabled = self.config.get('graph_enabled', False)
        self.graph_weight = self.config.get('graph_weight', 0.3) # Graph score weight

        # 컴포넌트 초기화
        self.embedding_model: Optional[Any] = None
        self.reranker: Optional[Any] = None
        self.collection: Optional[Any] = None
        self.pinecone_index: Optional[Any] = None
        self.voyage_client: Optional[Any] = None
        self.keyword_index: Dict[str, Any] = {} # BM25 대용 (In-memory simple index)
        
        # 간단 캐시 (쿼리 결과/임베딩)
        self.query_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.embedding_cache: Dict[str, List[float]] = {}
        self.embedding_model_name = self.config.get('embedding_model')
        # 벡터 DB 백엔드 - Pinecone을 기본으로 사용
        self.vector_backend = str(self.config.get('vector_db', 'pinecone')).lower()

        # Pinecone 설정
        self.pinecone_api_key = self.config.get('pinecone_api_key', '')
        self.pinecone_index_name = self.config.get('pinecone_index_name', 'creator-onboarding')
        self.pinecone_namespace = self.config.get('pinecone_namespace', 'default')

        # Embedding 설정
        self.embedding_provider = self.config.get('embedding_provider', 'voyage')
        self.voyage_api_key = self.config.get('voyage_api_key', '')
        self.voyage_model = self.config.get('voyage_embedding_model', 'voyage-3')

        self._initialize_components()
    
    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # Voyage AI 임베딩 클라이언트 초기화 (기본)
            if VOYAGE_AVAILABLE and voyageai is not None and self.voyage_api_key:
                try:
                    self.voyage_client = voyageai.Client(api_key=self.voyage_api_key)
                    self.logger.info(f"Voyage AI client initialized with model: {self.voyage_model}")
                except Exception as voyage_exc:
                    self.logger.warning(f"Voyage AI init failed: {voyage_exc}")
                    self.voyage_client = None

            # Pinecone 초기화 (기본 벡터 DB)
            if PINECONE_AVAILABLE and Pinecone is not None and self.pinecone_api_key:
                try:
                    pc = Pinecone(api_key=self.pinecone_api_key)
                    self.pinecone_index = pc.Index(self.pinecone_index_name)
                    self.logger.info(f"Pinecone initialized with index: {self.pinecone_index_name}")
                except Exception as pinecone_exc:
                    self.logger.warning(f"Pinecone init failed: {pinecone_exc}")
                    self.pinecone_index = None
            else:
                if self.vector_backend == 'pinecone':
                    self.logger.warning("Pinecone not available or API key not set")

            # SentenceTransformer 폴백 (Voyage 사용 불가 시)
            if not self.voyage_client and SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
                try:
                    embedding_name = self.embedding_model_name
                    if not embedding_name:
                        from config.settings import get_settings
                        embedding_name = get_settings().EMBEDDING_MODEL_NAME or 'all-MiniLM-L6-v2'
                    embedding_name = self._resolve_embedding_model_name(embedding_name)
                    self.embedding_model = SentenceTransformer(embedding_name)
                    self.logger.info(f"SentenceTransformer fallback initialized: {embedding_name}")
                except Exception as embed_exc:
                    self.logger.warning(f"Embedding model init failed ({embed_exc})")
                    self.embedding_model = None

            # Reranker 초기화 (Cross-Encoder)
            if SENTENCE_TRANSFORMERS_AVAILABLE and CrossEncoder is not None:
                try:
                    # 다국어 Reranker 추천: 'BAAI/bge-reranker-v2-m3' (Strongest)
                    # 여기서는 lightweight fallback 사용
                    self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                    self.logger.info("Reranker initialized (ms-marco-MiniLM-L-6-v2)")
                except Exception as rerank_exc:
                    self.logger.warning(f"Reranker init failed: {rerank_exc}")
                    self.reranker = None

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            self.embedding_model = None
            self.reranker = None
            self.pinecone_index = None
            self.voyage_client = None

    def _extract_tags(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """
        GraphRAG-lite를 위한 태그(엔티티/키워드) 추출.
        - 외부 형태소 분석 없이도 동작하는 "실용적" 휴리스틱
        - 목적: _graph_search가 실제로 의미 있게 동작하도록 keyword_index metadata['tags']를 채움
        """
        tags: List[str] = []
        try:
            # 1) 메타데이터 기반 태그 우선
            for key in ("tags", "keywords"):
                v = metadata.get(key)
                if isinstance(v, list):
                    tags.extend([str(x).strip() for x in v if str(x).strip()])
                elif isinstance(v, str) and v.strip():
                    tags.extend([t.strip() for t in v.split(",") if t.strip()])

            for key in ("source", "title", "category"):
                v = metadata.get(key)
                if isinstance(v, str) and v.strip():
                    tags.append(v.strip())

            # 2) 본문에서 해시태그/영문 토큰/한글 토큰 추출
            text = content or ""
            hashtags = re.findall(r"#([\\w가-힣]{2,})", text)
            tags.extend(hashtags)

            # 단어 토큰화(공백/기호 기반) + 최소 길이 필터
            raw_tokens = re.split(r"[\\s\\t\\n\\r\\.,;:!\\?\\(\\)\\[\\]\\{\\}<>\\-_/\\\\\\\"']+", text)
            stop = {
                "the","and","for","with","this","that","from","are","was","were","will","your",
                "있습니다","합니다","그리고","하지만","또한","관련","사용","기능","목적","위해","대한","그것","이것","저것"
            }
            for tok in raw_tokens:
                t = tok.strip()
                if len(t) < 3:
                    continue
                if t.lower() in stop:
                    continue
                # 숫자만/기호만 제거
                if re.fullmatch(r"\\d+", t):
                    continue
                tags.append(t)

            # 3) 정리: 중복 제거 + 상한
            seen = set()
            out: List[str] = []
            for t in tags:
                tt = str(t).strip()
                if not tt:
                    continue
                key = tt.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(tt)
                if len(out) >= 30:
                    break
            return out
        except Exception:
            return []
    
    def _resolve_embedding_model_name(self, candidate: str) -> str:
        if not candidate:
            return "all-MiniLM-L6-v2"
        normalized = candidate.strip()
        if "text-embedding" in normalized or "voyage" in normalized:
            self.logger.warning(
                f"Embedding model '{normalized}' requires external API support; "
                "falling back to 'all-MiniLM-L6-v2' inside RetrievalEngine."
            )
            return "all-MiniLM-L6-v2"
        return normalized
    
    async def vector_search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """벡터 검색 - Pinecone 기본"""
        try:
            cache_key = f"vec::{query}::{limit}::{str(filters)}"
            if cache_key in self.query_cache:
                return self.query_cache[cache_key][:]

            query_embedding = await self._get_embedding(query)

            if self.pinecone_index and self.vector_backend == 'pinecone':
                search_results = await self._pinecone_search(query_embedding, limit, filters)
            elif self.collection:
                # ChromaDB 폴백 logic...
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where=filters
                )
                search_results = []
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        result = {
                            "id": results['ids'][0][i],
                            "content": doc,
                            "score": 1 - results['distances'][0][i],
                            "metadata": results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                            "search_type": "vector"
                        }
                        search_results.append(result)
            else:
                return await self._fallback_vector_search(query, limit, filters)

            # GraphRAG-lite: pinecone/vector 결과도 keyword_index에 반영해 graph_search가 동작하도록 함
            try:
                for r in search_results:
                    doc_id = r.get("id") or ""
                    if not doc_id:
                        continue
                    meta = r.get("metadata") or {}
                    if not isinstance(meta, dict):
                        meta = {}
                    content = r.get("content") or meta.get("content") or ""
                    if not isinstance(content, str):
                        content = str(content)
                    # tags 보강
                    meta.setdefault("tags", self._extract_tags(content, meta))
                    self.keyword_index[doc_id] = {"content": content, "metadata": meta}
            except Exception:
                pass

            self.query_cache[cache_key] = search_results[:]
            return search_results

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return await self._fallback_vector_search(query, limit, filters)

    async def _get_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        embedding: List[float] = []

        if self.voyage_client:
            try:
                result = self.voyage_client.embed(
                    texts=[text],
                    model=self.voyage_model,
                    input_type="query"
                )
                embedding = result.embeddings[0]
            except Exception as e:
                self.logger.warning(f"Voyage embedding failed: {e}")

        if not embedding and self.embedding_model:
            embedding = self.embedding_model.encode([text])[0].tolist()

        if not embedding:
            embedding = self._simple_hash_embedding(text)

        self.embedding_cache[text] = embedding
        return embedding

    async def _pinecone_search(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        try:
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=limit,
                namespace=self.pinecone_namespace,
                include_metadata=True,
                filter=filters
            )

            search_results = []
            for match in results.get('matches', []):
                md = match.get('metadata', {}) or {}
                result = {
                    "id": match.get('id', ''),
                    "content": md.get('content', ''),
                    "score": match.get('score', 0.0),
                    "metadata": md,
                    "search_type": "vector_pinecone"
                }
                search_results.append(result)

            return search_results

        except Exception as e:
            self.logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """키워드 검색 (Simple BM25-like)"""
        try:
            cache_key = f"kw::{query}::{limit}"
            if cache_key in self.query_cache:
                return self.query_cache[cache_key][:]
                
            query_terms = query.lower().split()
            results = []
            
            for doc_id, doc_info in self.keyword_index.items():
                content = doc_info.get('content', '').lower()
                metadata = doc_info.get('metadata', {})
                
                score = 0
                for term in query_terms:
                    if term in content:
                        score += content.count(term)
                
                if score > 0:
                    normalized_score = min(score / (len(content.split()) + 1), 1.0) # Simple normalization
                    
                    result = {
                        "id": doc_id,
                        "content": doc_info.get('content', ''),
                        "score": normalized_score,
                        "metadata": metadata,
                        "search_type": "keyword"
                    }
                    results.append(result)
            
            results.sort(key=lambda x: x['score'], reverse=True)
            out = results[:limit]
            self.query_cache[cache_key] = out[:]
            return out
            
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []

    async def _graph_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        [2025 Trend] GraphRAG Simulation
        Ideally, this traverses a Knowledge Graph. Here, we simulate graph traversal 
        by finding entities in the query and looking up related concepts in metadata.
        """
        try:
            # 1. Entity Extraction (Simulated)
            entities = [w for w in query.split() if len(w) > 2]
            
            graph_results = []
            
            # 2. Graph Traversal Simulation
            for doc_id, doc_info in self.keyword_index.items():
                metadata = doc_info.get('metadata', {})
                tags = metadata.get('tags', [])
                
                # Check for shared tags/entities (Edge traversal)
                score = 0
                for entity in entities:
                    if entity in tags or any(entity in str(t) for t in tags):
                        score += 1.0
                
                if score > 0:
                     result = {
                        "id": doc_id,
                        "content": doc_info.get('content', ''),
                        "score": score, # Graph relevance score
                        "metadata": metadata,
                        "search_type": "graph"
                    }
                     graph_results.append(result)

            graph_results.sort(key=lambda x: x['score'], reverse=True)
            return graph_results[:limit]
        except Exception as e:
            self.logger.error(f"Graph search failed: {e}")
            return []
    
    async def hybrid_search(
        self, 
        query: str, 
        limit: int = 20, # Fetch more candidates for reranking
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Wrtn Style Hybrid Search with GraphRAG integration (2025).
        Executes Vector, Keyword, and Graph search in parallel.
        """
        try:
            tasks = [
                self.vector_search(query, limit, filters),
                self.keyword_search(query, limit)
            ]
            
            if self.graph_enabled:
                 tasks.append(self._graph_search(query, limit))

            results_tuple = await asyncio.gather(*tasks)
            
            vector_results = results_tuple[0]
            keyword_results = results_tuple[1]
            graph_results = results_tuple[2] if self.graph_enabled and len(results_tuple) > 2 else []
            
            # 2. Merge Results
            combined_results = await self._merge_search_results(
                vector_results, keyword_results, graph_results, query
            )
            
            # 3. Reranking (Cross-Encoder)
            if self.reranker:
                final_results = await self.rerank_documents(query, combined_results, top_k=self.rerank_top_k)
            else:
                final_results = combined_results[:self.rerank_top_k]
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def rerank_documents(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Cross-Encoder based Reranking.
        Significantly improves precision by scoring the exact query-document pair.
        """
        try:
            if not documents:
                return []

            if not self.reranker:
                # Fallback to sort by initial score
                documents.sort(key=lambda x: x.get('score', 0), reverse=True)
                return documents[:top_k]
            
            # Prepare pairs for Cross-Encoder
            doc_texts = [d.get('content', '') for d in documents]
            pairs = [[query, doc_text] for doc_text in doc_texts]
            
            # Predict scores
            scores = self.reranker.predict(pairs)
            
            # Update scores and sort
            for i, doc in enumerate(documents):
                doc['rerank_score'] = float(scores[i])
                doc['original_score'] = doc.get('score', 0)
                doc['score'] = float(scores[i]) # Overwrite main score for downstream consistency
                
            documents.sort(key=lambda x: x['score'], reverse=True)
            
            return documents[:top_k]
            
        except Exception as e:
            self.logger.error(f"Document reranking failed: {e}")
            return documents[:top_k]
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """문서 추가"""
        try:
            if not self.collection:
                return await self._fallback_add_documents(documents)
            
            texts: List[str] = []
            metadatas = []
            ids = []
            embeddings = []
            
            for doc in documents:
                doc_id = doc.get('id', f"doc_{len(texts)}")
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                metadata['timestamp'] = datetime.now().isoformat()
                metadata.setdefault("tags", self._extract_tags(content, metadata))
                
                texts.append(content)
                metadatas.append(metadata)
                ids.append(doc_id)
                
                if self.embedding_model:
                    embedding = self.embedding_model.encode([content])[0].tolist()
                else:
                    embedding = self._simple_hash_embedding(content)
                embeddings.append(embedding)
                
                self.keyword_index[doc_id] = {
                    'content': content,
                    'metadata': metadata
                }
            
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Added {len(documents)} documents to search index")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {e}")
            return await self._fallback_add_documents(documents)
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """문서 삭제"""
        try:
            if not self.collection:
                return await self._fallback_delete_documents(document_ids)
            
            self.collection.delete(ids=document_ids)
            
            for doc_id in document_ids:
                self.keyword_index.pop(doc_id, None)
            
            self.logger.info(f"Deleted {len(document_ids)} documents from search index")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete documents: {e}")
            return await self._fallback_delete_documents(document_ids)
    
    async def _merge_search_results(
        self, 
        vector_results: List[Dict[str, Any]], 
        keyword_results: List[Dict[str, Any]], 
        graph_results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """검색 결과 병합 (Weighted Sum including GraphRAG)"""
        try:
            result_map = {}
            
            # Vector Results
            for result in vector_results:
                doc_id = result['id']
                result['vector_score'] = result['score']
                result['keyword_score'] = 0.0
                result['graph_score'] = 0.0
                result_map[doc_id] = result
            
            # Keyword Results
            for result in keyword_results:
                doc_id = result['id']
                if doc_id in result_map:
                    result_map[doc_id]['keyword_score'] = result['score']
                else:
                    result['vector_score'] = 0.0
                    result['keyword_score'] = result['score']
                    result['graph_score'] = 0.0
                    result_map[doc_id] = result

            # Graph Results
            for result in graph_results:
                 doc_id = result['id']
                 if doc_id in result_map:
                     result_map[doc_id]['graph_score'] = result['score']
                 else:
                     result['vector_score'] = 0.0
                     result['keyword_score'] = 0.0
                     result['graph_score'] = result['score']
                     result_map[doc_id] = result
            
            merged_results = []
            for result in result_map.values():
                # Weighted Sum
                final_score = (
                    result['vector_score'] * self.vector_weight +
                    result['keyword_score'] * self.keyword_weight + 
                    result['graph_score'] * self.graph_weight
                )
                result['score'] = final_score
                merged_results.append(result)
            
            return merged_results
            
        except Exception as e:
            self.logger.error(f"Search result merging failed: {e}")
            return vector_results + keyword_results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_ids = set()
        unique_results = []
        for result in results:
            doc_id = result.get('id', '')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)
        return unique_results
    
    async def _fallback_vector_search(
        self, 
        query: str, 
        limit: int, 
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        try:
            return await self.keyword_search(query, limit)
        except Exception as e:
            self.logger.error(f"Fallback vector search failed: {e}")
            return []
    
    async def _fallback_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        try:
            for doc in documents:
                doc_id = doc.get('id', f"doc_{len(self.keyword_index)}")
                md = doc.get('metadata', {}) or {}
                if not isinstance(md, dict):
                    md = {}
                content = doc.get('content', '') or ''
                if not isinstance(content, str):
                    content = str(content)
                md.setdefault("tags", self._extract_tags(content, md))
                self.keyword_index[doc_id] = {
                    'content': content,
                    'metadata': md
                }
            return True
        except Exception as e:
            self.logger.error(f"Fallback add documents failed: {e}")
            return False
    
    async def _fallback_delete_documents(self, document_ids: List[str]) -> bool:
        try:
            for doc_id in document_ids:
                self.keyword_index.pop(doc_id, None)
            return True
        except Exception as e:
            self.logger.error(f"Fallback delete documents failed: {e}")
            return False
    
    def _simple_hash_embedding(self, text: str) -> List[float]:
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        embedding = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            embedding.append(val)
        
        while len(embedding) < 128:
            embedding.append(0.0)
        
        return embedding[:128]
    
    async def get_search_stats(self) -> Dict[str, Any]:
        try:
            stats = {
                'total_documents': len(self.keyword_index),
                'vector_store_available': self.collection is not None,
                'embedding_model_available': self.embedding_model is not None,
                'reranker_available': self.reranker is not None,
                'search_config': {
                    'vector_weight': self.vector_weight,
                    'keyword_weight': self.keyword_weight,
                    'graph_weight': self.graph_weight,
                    'max_results': self.max_results,
                    'similarity_threshold': self.similarity_threshold
                }
            }
            if self.collection:
                try:
                    stats['vector_store_count'] = self.collection.count()
                except Exception:
                    stats['vector_store_count'] = 0
            return stats
        except Exception as e:
            self.logger.error(f"Search stats retrieval failed: {e}")
            return {'error': str(e)}
