"""검색 엔진 구현"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json  # noqa: F401

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
    """검색 엔진"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("RetrievalEngine")

        # 검색 설정
        self.vector_weight = self.config.get('vector_weight', 0.7)
        self.keyword_weight = self.config.get('keyword_weight', 0.3)
        self.max_results = self.config.get('max_results', 10)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.5)

        # 컴포넌트 초기화
        self.embedding_model: Optional[Any] = None
        self.reranker: Optional[Any] = None
        self.collection: Optional[Any] = None
        self.pinecone_index: Optional[Any] = None
        self.voyage_client: Optional[Any] = None
        self.keyword_index: Dict[str, Any] = {}
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

            # Reranker 초기화
            if SENTENCE_TRANSFORMERS_AVAILABLE and CrossEncoder is not None:
                try:
                    self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
                    self.logger.info("Reranker initialized")
                except Exception as rerank_exc:
                    self.logger.warning(f"Reranker init failed: {rerank_exc}")
                    self.reranker = None

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            self.embedding_model = None
            self.reranker = None
            self.pinecone_index = None
            self.voyage_client = None
    
    def _resolve_embedding_model_name(self, candidate: str) -> str:
        """
        Map configured embedding model names to SentenceTransformer-compatible models.
        """
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
            # 캐시 히트
            cache_key = f"vec::{query}::{limit}::{str(filters)}"
            if cache_key in self.query_cache:
                return self.query_cache[cache_key][:]

            # 쿼리 임베딩 생성
            query_embedding = await self._get_embedding(query)

            # Pinecone 검색 (기본)
            if self.pinecone_index and self.vector_backend == 'pinecone':
                search_results = await self._pinecone_search(query_embedding, limit, filters)
            elif self.collection:
                # ChromaDB 폴백
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

            self.query_cache[cache_key] = search_results[:]
            return search_results

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return await self._fallback_vector_search(query, limit, filters)

    async def _get_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 - Voyage AI 우선"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        embedding: List[float] = []

        # Voyage AI 사용 (기본)
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

        # SentenceTransformer 폴백
        if not embedding and self.embedding_model:
            embedding = self.embedding_model.encode([text])[0].tolist()

        # 최종 폴백
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
        """Pinecone 검색"""
        try:
            # Pinecone 쿼리
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=limit,
                namespace=self.pinecone_namespace,
                include_metadata=True,
                filter=filters
            )

            search_results = []
            for match in results.get('matches', []):
                result = {
                    "id": match.get('id', ''),
                    "content": match.get('metadata', {}).get('content', ''),
                    "score": match.get('score', 0.0),
                    "metadata": match.get('metadata', {}),
                    "search_type": "vector_pinecone"
                }
                search_results.append(result)

            return search_results

        except Exception as e:
            self.logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def keyword_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """키워드 검색"""
        try:
            cache_key = f"kw::{query}::{limit}"
            if cache_key in self.query_cache:
                return self.query_cache[cache_key][:]
            # 간단한 키워드 매칭 검색
            query_terms = query.lower().split()
            results = []
            
            # 메모리 기반 키워드 인덱스에서 검색
            for doc_id, doc_info in self.keyword_index.items():
                content = doc_info.get('content', '').lower()
                metadata = doc_info.get('metadata', {})
                
                # 키워드 매칭 점수 계산
                score = 0
                for term in query_terms:
                    if term in content:
                        score += content.count(term)
                
                if score > 0:
                    # 정규화된 점수
                    normalized_score = min(score / len(content.split()), 1.0)
                    
                    result = {
                        "id": doc_id,
                        "content": doc_info.get('content', ''),
                        "score": normalized_score,
                        "metadata": metadata,
                        "search_type": "keyword"
                    }
                    results.append(result)
            
            # 점수순 정렬
            results.sort(key=lambda x: x['score'], reverse=True)
            out = results[:limit]
            self.query_cache[cache_key] = out[:]
            return out
            
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []
    
    async def hybrid_search(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 키워드)"""
        try:
            # 병렬 실행으로 레이턴시 단축
            import asyncio
            vector_results, keyword_results = await asyncio.gather(
                self.vector_search(query, limit, filters),
                self.keyword_search(query, limit)
            )
            
            # 결과 병합 및 점수 조정
            combined_results = await self._merge_search_results(
                vector_results, keyword_results, query
            )
            
            # 중복 제거
            unique_results = self._deduplicate_results(combined_results)
            
            # 최종 정렬
            unique_results.sort(key=lambda x: x['score'], reverse=True)
            
            return unique_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def rerank_documents(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """문서 재순위화"""
        try:
            # 설정에서 임계값/확장 플래그 로드
            try:
                from config.settings import get_settings
                st = get_settings()
                threshold = float(getattr(st, 'RERANKER_THRESHOLD', 0.0))
                expansion = bool(getattr(st, 'QUERY_EXPANSION_ENABLED', False))
            except Exception:
                threshold = 0.0
                expansion = False
            if not self.reranker or len(documents) <= top_k:
                # 임계값 필터만 적용
                docs = documents[:top_k]
                return [d for d in docs if float(d.get('score', 0.0)) >= threshold]
            
            # 재순위화 수행
            query_doc_pairs = [(query, doc['content']) for doc in documents]
            rerank_scores = self.reranker.predict(query_doc_pairs)
            
            # 점수와 함께 정렬 및 간단 boost/임계값 적용
            reranked_docs = []
            boost_terms: List[str] = []
            if expansion:
                toks = [t for t in query.split() if len(t) > 2]
                boost_terms = toks[:3]
            for doc, score in zip(documents, rerank_scores):
                base = float(doc.get('score', 0.0))
                r = float(score)
                final = (base + r) / 2
                if boost_terms and any(term.lower() in doc.get('content', '').lower() for term in boost_terms):
                    final = min(final + 0.05, 1.0)
                if final >= threshold:
                    nd = dict(doc)
                    nd['rerank_score'] = r
                    nd['final_score'] = final
                    reranked_docs.append(nd)
            reranked_docs.sort(key=lambda x: x['final_score'], reverse=True)
            return reranked_docs[:top_k]
            
        except Exception as e:
            self.logger.error(f"Document reranking failed: {e}")
            return documents[:top_k]
    
    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """문서 추가"""
        try:
            if not self.collection:
                return await self._fallback_add_documents(documents)
            
            # 문서 처리
            texts: List[str] = []
            metadatas = []
            ids = []
            embeddings = []
            
            for doc in documents:
                doc_id = doc.get('id', f"doc_{len(texts)}")
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                metadata['timestamp'] = datetime.now().isoformat()
                
                texts.append(content)
                metadatas.append(metadata)
                ids.append(doc_id)
                
                # 임베딩 생성
                if self.embedding_model:
                    embedding = self.embedding_model.encode([content])[0].tolist()
                else:
                    embedding = self._simple_hash_embedding(content)
                embeddings.append(embedding)
                
                # 키워드 인덱스에 추가
                self.keyword_index[doc_id] = {
                    'content': content,
                    'metadata': metadata
                }
            
            # ChromaDB에 추가
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
            
            # ChromaDB에서 삭제
            self.collection.delete(ids=document_ids)
            
            # 키워드 인덱스에서도 삭제
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
        query: str
    ) -> List[Dict[str, Any]]:
        """검색 결과 병합"""
        try:
            # 결과 ID별로 그룹화
            result_map = {}
            
            # 벡터 검색 결과 추가
            for result in vector_results:
                doc_id = result['id']
                result['vector_score'] = result['score']
                result['keyword_score'] = 0.0
                result_map[doc_id] = result
            
            # 키워드 검색 결과 병합
            for result in keyword_results:
                doc_id = result['id']
                if doc_id in result_map:
                    # 기존 결과에 키워드 점수 추가
                    result_map[doc_id]['keyword_score'] = result['score']
                else:
                    # 새로운 결과 추가
                    result['vector_score'] = 0.0
                    result['keyword_score'] = result['score']
                    result_map[doc_id] = result
            
            # 최종 점수 계산
            merged_results = []
            for result in result_map.values():
                # 가중 평균 점수
                final_score = (
                    result['vector_score'] * self.vector_weight +
                    result['keyword_score'] * self.keyword_weight
                )
                result['score'] = final_score
                merged_results.append(result)
            
            return merged_results
            
        except Exception as e:
            self.logger.error(f"Search result merging failed: {e}")
            return vector_results + keyword_results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """결과 중복 제거"""
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
        """폴백 벡터 검색"""
        try:
            # 키워드 검색으로 대체
            return await self.keyword_search(query, limit)
            
        except Exception as e:
            self.logger.error(f"Fallback vector search failed: {e}")
            return []
    
    async def _fallback_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """폴백 문서 추가"""
        try:
            for doc in documents:
                doc_id = doc.get('id', f"doc_{len(self.keyword_index)}")
                self.keyword_index[doc_id] = {
                    'content': doc.get('content', ''),
                    'metadata': doc.get('metadata', {})
                }
            return True
            
        except Exception as e:
            self.logger.error(f"Fallback add documents failed: {e}")
            return False
    
    async def _fallback_delete_documents(self, document_ids: List[str]) -> bool:
        """폴백 문서 삭제"""
        try:
            for doc_id in document_ids:
                self.keyword_index.pop(doc_id, None)
            return True
            
        except Exception as e:
            self.logger.error(f"Fallback delete documents failed: {e}")
            return False
    
    def _simple_hash_embedding(self, text: str) -> List[float]:
        """간단한 해시 기반 임베딩 (폴백)"""
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # 128차원 벡터로 변환
        embedding = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            embedding.append(val)
        
        # 128차원으로 패딩
        while len(embedding) < 128:
            embedding.append(0.0)
        
        return embedding[:128]
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """검색 통계 조회"""
        try:
            stats = {
                'total_documents': len(self.keyword_index),
                'vector_store_available': self.collection is not None,
                'embedding_model_available': self.embedding_model is not None,
                'reranker_available': self.reranker is not None,
                'search_config': {
                    'vector_weight': self.vector_weight,
                    'keyword_weight': self.keyword_weight,
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
