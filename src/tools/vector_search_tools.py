"""벡터 검색 도구"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Optional imports with fallback
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore

# Optional OpenAI embeddings via LangChain
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_EMBEDDINGS_AVAILABLE = True
except Exception:
    OPENAI_EMBEDDINGS_AVAILABLE = False
    OpenAIEmbeddings = None  # type: ignore

# Optional Voyage AI embeddings
try:
    import voyageai  # type: ignore
    VOYAGE_AVAILABLE = True
except Exception:
    VOYAGE_AVAILABLE = False
    voyageai = None  # type: ignore

# Optional Pinecone vector DB
try:
    import pinecone  # type: ignore
    PINECONE_AVAILABLE = True
except Exception:
    PINECONE_AVAILABLE = False
    pinecone = None  # type: ignore

logger = logging.getLogger(__name__)


class VectorSearchTool:
    """벡터 검색 도구"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.embedding_model: Optional[Any] = None  # SentenceTransformer instance
        self.openai_embeddings: Optional[Any] = None  # OpenAIEmbeddings instance
        self.voyage_client: Optional[Any] = None  # voyageai.Client instance
        self.embedding_backend: str = "fallback"  # one of: openai|sentence|fallback
        self.collection: Optional[Any] = None
        # Pinecone
        self.pinecone_enabled: bool = False
        self.pinecone_index_name: Optional[str] = None
        self.pinecone_index: Optional[Any] = None
        self._initialize_components()

    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 임베딩 모델 초기화 (선택적)
            from config.settings import get_settings
            emb_name = 'all-MiniLM-L6-v2'
            try:
                emb_name = get_settings().EMBEDDING_MODEL_NAME or emb_name
            except Exception:
                pass

            # OpenAI 임베딩 우선: text-embedding-* 패밀리 지정 시
            if (emb_name.startswith("text-embedding") and OPENAI_EMBEDDINGS_AVAILABLE):
                try:
                    self.openai_embeddings = OpenAIEmbeddings(model=emb_name)
                    self.embedding_backend = "openai"
                    logger.info("OpenAIEmbeddings initialized (%s)", emb_name)
                except Exception as oe:
                    logger.warning("OpenAIEmbeddings init failed, fallback to sentence/fallback: %s", oe)

            # Voyage 임베딩: voyage-* 지정 시
            if self.embedding_backend not in ("openai",) and emb_name.startswith("voyage-") and VOYAGE_AVAILABLE:
                try:
                    s = get_settings()
                    if s.VOYAGE_API_KEY:
                        self.voyage_client = voyageai.Client(api_key=s.VOYAGE_API_KEY)
                        self.embedding_backend = "voyage"
                        logger.info("VoyageAI embeddings initialized (%s)", emb_name)
                except Exception as ve:
                    logger.warning("VoyageAI init failed, fallback to sentence/fallback: %s", ve)

            # SentenceTransformers 백업 경로
            if self.embedding_backend != "openai":
                if self.embedding_backend != "voyage" and SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
                    self.embedding_model = SentenceTransformer(emb_name if not emb_name.startswith("text-embedding") else 'all-MiniLM-L6-v2')
                    self.embedding_backend = "sentence"
                    logger.info("SentenceTransformer initialized (%s)", emb_name)
                else:
                    self.embedding_model = None
                    self.embedding_backend = "fallback"
                    logger.warning("SentenceTransformer not available, using fallback")
            
            # Pinecone 클라이언트 초기화 (주 벡터 DB)
            from config.settings import get_settings
            s = get_settings()

            # Pinecone 우선 사용(키가 있는 경우)
            if PINECONE_AVAILABLE and s.PINECONE_API_KEY:
                try:
                    pinecone.init(api_key=s.PINECONE_API_KEY, environment=s.PINECONE_ENVIRONMENT)  # type: ignore
                    self.pinecone_enabled = True
                    self.pinecone_index_name = s.PINECONE_INDEX_NAME or "documents"
                    logger.info("Pinecone initialized (env=%s, index=%s)", s.PINECONE_ENVIRONMENT, self.pinecone_index_name)
                except Exception as pe:
                    logger.warning("Pinecone init failed, fallback to Chroma: %s", pe)
                    self.pinecone_enabled = False

            # Pinecone가 없으면 메모리 기반으로 폴백한다.
            if not self.pinecone_enabled:
                self.collection = None
                logger.info("Pinecone disabled; using in-memory vector search fallback")
                
            logger.info("Vector search tool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector search tool: {e}")
            # 폴백: 메모리 기반 저장소
            self.documents = {}
            self.embeddings = {}
            self.embedding_model = None
            self.chroma_client = None
            self.collection = None

    async def search(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """벡터 검색 수행"""
        try:
            if self.pinecone_enabled:
                return self._pinecone_search(query, limit)
            if self.collection is None:
                return self._fallback_search(query, limit, filters)
            
            # 현재는 Pinecone를 기본 백엔드로 사용하고,
            # 컬렉션 기반 로컬 벡터 스토어는 사용하지 않는다.
            return self._fallback_search(query, limit, filters)
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return self._fallback_search(query, limit, filters)

    def _fallback_search(self, query: str, limit: int, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """폴백 검색 (메모리 기반)"""
        try:
            # 간단한 키워드 매칭 검색
            results = []
            query_lower = query.lower()
            
            for doc_id, doc_data in self.documents.items():
                if isinstance(doc_data, dict) and 'content' in doc_data:
                    content = doc_data['content'].lower()
                    if query_lower in content:
                        score = content.count(query_lower) / len(content.split())
                        results.append({
                            "id": doc_id,
                            "content": doc_data['content'],
                            "score": min(score, 1.0),
                            "metadata": doc_data.get('metadata', {})
                        })
            
            # 점수순 정렬
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return [{
                "id": "fallback",
                "content": f"검색 결과: {query}",
                "score": 0.5,
                "metadata": {"source": "fallback"}
            }]

    async def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """문서 추가"""
        try:
            if self.pinecone_enabled:
                return self._pinecone_add_documents(documents)
            if self.collection is None:
                return self._fallback_add_documents(documents)
            
            # 문서 텍스트 추출
            texts = []
            metadatas = []
            ids = []
            
            for doc in documents:
                doc_id = doc.get('id', str(uuid.uuid4()))
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                metadata['timestamp'] = datetime.now().isoformat()
                
                texts.append(content)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            # 임베딩 생성
            embeddings = self._embed_texts(texts)
            
            # ChromaDB에 추가
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return self._fallback_add_documents(documents)

    def _fallback_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """폴백 문서 추가 (메모리 기반)"""
        try:
            for doc in documents:
                doc_id = doc.get('id', str(uuid.uuid4()))
                self.documents[doc_id] = doc
            return True
        except Exception as e:
            logger.error(f"Fallback add documents failed: {e}")
            return False

    async def delete_documents(self, document_ids: List[str]) -> bool:
        """문서 삭제"""
        try:
            if self.collection is None:
                return self._fallback_delete_documents(document_ids)
            
            # ChromaDB에서 삭제
            self.collection.delete(ids=document_ids)
            
            logger.info(f"Deleted {len(document_ids)} documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return self._fallback_delete_documents(document_ids)

    def _fallback_delete_documents(self, document_ids: List[str]) -> bool:
        """폴백 문서 삭제 (메모리 기반)"""
        try:
            for doc_id in document_ids:
                if doc_id in self.documents:
                    del self.documents[doc_id]
            return True
        except Exception as e:
            logger.error(f"Fallback delete documents failed: {e}")
            return False

    async def get_document_count(self) -> int:
        """문서 수 조회"""
        try:
            if self.collection is None:
                return len(self.documents)
            
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

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

    def _embed_query(self, query: str) -> List[float]:
        """쿼리 임베딩 생성(OpenAI→Sentence→폴백 순)."""
        try:
            if self.embedding_backend == "openai" and self.openai_embeddings is not None:
                vec = self.openai_embeddings.embed_query(query)
                return list(map(float, vec))
            if self.embedding_backend == "voyage" and self.voyage_client is not None:
                from config.settings import get_settings
                model = get_settings().EMBEDDING_MODEL_NAME
                resp = self.voyage_client.embed(texts=[query], model=model)
                return list(map(float, resp.embeddings[0]))
            if self.embedding_backend == "sentence" and self.embedding_model is not None:
                return self.embedding_model.encode([query])[0].tolist()
        except Exception as e:
            logger.warning("Query embedding failed, using fallback: %s", e)
        return self._simple_hash_embedding(query)

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """문서 임베딩 생성(OpenAI→Sentence→폴백 순)."""
        try:
            if self.embedding_backend == "openai" and self.openai_embeddings is not None:
                vecs = self.openai_embeddings.embed_documents(texts)
                return [list(map(float, v)) for v in vecs]
            if self.embedding_backend == "voyage" and self.voyage_client is not None:
                from config.settings import get_settings
                model = get_settings().EMBEDDING_MODEL_NAME
                resp = self.voyage_client.embed(texts=texts, model=model)
                return [list(map(float, v)) for v in resp.embeddings]
            if self.embedding_backend == "sentence" and self.embedding_model is not None:
                return self.embedding_model.encode(texts).tolist()
        except Exception as e:
            logger.warning("Texts embedding failed, using fallback: %s", e)
        return [self._simple_hash_embedding(t) for t in texts]

    def _ensure_pinecone_index(self, dimension: int) -> None:
        if not self.pinecone_enabled or self.pinecone_index_name is None:
            return
        try:
            existing = [i["name"] for i in pinecone.list_indexes()]  # type: ignore
            if self.pinecone_index_name not in existing:
                pinecone.create_index(name=self.pinecone_index_name, dimension=dimension, metric="cosine")  # type: ignore
            self.pinecone_index = pinecone.Index(self.pinecone_index_name)  # type: ignore
        except Exception as e:
            logger.warning("Ensure Pinecone index failed: %s", e)

    def _pinecone_add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        try:
            texts: List[str] = []
            ids: List[str] = []
            metadatas: List[Dict[str, Any]] = []
            for doc in documents:
                ids.append(doc.get('id', str(uuid.uuid4())))
                texts.append(doc.get('content', ''))
                md = doc.get('metadata', {})
                md['timestamp'] = datetime.now().isoformat()
                metadatas.append(md)
            vectors = self._embed_texts(texts)
            if not vectors:
                return False
            self._ensure_pinecone_index(len(vectors[0]))
            if not self.pinecone_index:
                return False
            # upsert
            items = []
            for i, vec in enumerate(vectors):
                items.append({"id": ids[i], "values": vec, "metadata": metadatas[i]})
            self.pinecone_index.upsert(vectors=items)  # type: ignore
            logger.info("Upserted %d vectors to Pinecone", len(items))
            return True
        except Exception as e:
            logger.error("Pinecone add documents failed: %s", e)
            return False

    def _pinecone_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        try:
            qv = self._embed_query(query)
            self._ensure_pinecone_index(len(qv))
            if not self.pinecone_index:
                return []
            res = self.pinecone_index.query(vector=qv, top_k=limit, include_metadata=True)  # type: ignore
            out: List[Dict[str, Any]] = []
            for m in getattr(res, 'matches', []) or []:
                out.append({
                    "id": getattr(m, 'id', ''),
                    "content": (m.metadata or {}).get('content', ''),
                    "score": float(getattr(m, 'score', 0.0)),
                    "metadata": m.metadata or {}
                })
            return out
        except Exception as e:
            logger.error("Pinecone search failed: %s", e)
            return []