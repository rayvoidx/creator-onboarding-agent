"""Langfuse 통합 모니터링"""

import logging
from typing import Dict, Any, Optional, List
import os

# 선택적 import
try:
    from langfuse import Langfuse  # type: ignore
    from langfuse.callback import CallbackHandler  # type: ignore
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None
    CallbackHandler = None

logger = logging.getLogger(__name__)


class LangfuseIntegration:
    """Langfuse 통합 모니터링"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("LangfuseIntegration")
        
        # Langfuse 설정
        self.public_key = self.config.get('public_key') or os.getenv('LANGFUSE_PUBLIC_KEY')
        self.secret_key = self.config.get('secret_key') or os.getenv('LANGFUSE_SECRET_KEY')
        self.host = self.config.get('host') or os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
        
        # Langfuse 클라이언트 초기화
        self.langfuse = None
        self.callback_handler = None
        
        if LANGFUSE_AVAILABLE and self.public_key and self.secret_key:
            self._initialize_langfuse()
        else:
            self.logger.warning("Langfuse not available or not configured")
    
    def _initialize_langfuse(self):
        """Langfuse 초기화"""
        try:
            self.langfuse = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            
            self.callback_handler = CallbackHandler(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            
            self.logger.info("Langfuse initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Langfuse: {e}")
            self.langfuse = None
            self.callback_handler = None
    
    async def start_trace(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """추적 시작"""
        try:
            if not self.langfuse:
                return None
            
            trace = self.langfuse.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
            
            return trace.id
            
        except Exception as e:
            self.logger.error(f"Failed to start trace: {e}")
            return None
    
    async def end_trace(
        self,
        trace_id: str,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """추적 종료"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.trace(
                id=trace_id,
                output=output,
                metadata=metadata or {}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to end trace: {e}")
            return False
    
    async def log_generation(
        self,
        trace_id: str,
        name: str,
        input_data: Any,
        output_data: Any,
        model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """생성 로그"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.generation(
                trace_id=trace_id,
                name=name,
                input=input_data,
                output=output_data,
                model=model,
                metadata=metadata or {}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log generation: {e}")
            return False
    
    async def log_retrieval(
        self,
        trace_id: str,
        name: str,
        query: str,
        documents: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """검색 로그"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.span(
                trace_id=trace_id,
                name=name,
                input={"query": query},
                output={"documents": documents},
                metadata=metadata or {}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log retrieval: {e}")
            return False
    
    async def log_agent_execution(
        self,
        trace_id: str,
        agent_name: str,
        input_data: Any,
        output_data: Any,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """에이전트 실행 로그"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.span(
                trace_id=trace_id,
                name=f"agent_{agent_name}",
                input=input_data,
                output=output_data,
                metadata={
                    **(metadata or {}),
                    "execution_time": execution_time,
                    "agent_name": agent_name
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log agent execution: {e}")
            return False
    
    async def log_rag_pipeline(
        self,
        trace_id: str,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        response: str,
        processing_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """RAG 파이프라인 로그"""
        try:
            if not self.langfuse:
                return False
            
            # 검색 단계
            await self.log_retrieval(
                trace_id=trace_id,
                name="document_retrieval",
                query=query,
                documents=retrieved_docs,
                metadata=metadata
            )
            
            # 생성 단계
            await self.log_generation(
                trace_id=trace_id,
                name="response_generation",
                input_data={"query": query, "context": retrieved_docs},
                output_data=response,
                model="rag_pipeline",
                metadata={
                    **(metadata or {}),
                    "processing_time": processing_time,
                    "num_documents": len(retrieved_docs)
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log RAG pipeline: {e}")
            return False
    
    async def log_performance_metrics(
        self,
        trace_id: str,
        metrics: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """성능 메트릭 로그"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.span(
                trace_id=trace_id,
                name="performance_metrics",
                input={},
                output=metrics,
                metadata=metadata or {}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log performance metrics: {e}")
            return False
    
    def get_callback_handler(self) -> Optional[CallbackHandler]:
        """콜백 핸들러 반환"""
        return self.callback_handler
    
    async def flush(self) -> bool:
        """데이터 플러시"""
        try:
            if not self.langfuse:
                return False
            
            self.langfuse.flush()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to flush Langfuse data: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        try:
            return {
                'available': LANGFUSE_AVAILABLE,
                'configured': bool(self.public_key and self.secret_key),
                'connected': self.langfuse is not None,
                'host': self.host
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'available': False,
                'configured': False,
                'connected': False,
                'error': str(e)
            }
