"""
외부 데이터 수집 에이전트

국가평생교육진흥원, 보건복지부, 육아정책연구소 등 외부 API에서
교육자료, 정책문서, 연구데이터를 수집하고 처리합니다.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ...core.base import BaseAgent, BaseState  # type: ignore[import-not-found]
from ...data.models.data_models import (  # type: ignore[import-not-found]
    ContentMetadata,
    CollectionStatus,
    ContentType
)
from ...utils.agent_config import get_agent_runtime_config

logger = logging.getLogger(__name__)

class DataSourceType(Enum):
    """데이터 소스 유형"""
    NILE = "nile"  # 국가평생교육진흥원
    MOHW = "mohw"  # 보건복지부
    KICCE = "kicce"  # 육아정책연구소
    MANUAL = "manual"  # 수동 업로드

@dataclass
class CollectionConfig:
    """수집 설정"""
    source_type: DataSourceType
    api_key: str
    base_url: str
    collection_interval: int  # 분 단위
    max_items_per_request: int = 100
    retry_count: int = 3
    timeout: int = 30

class DataCollectionState(BaseState):
    """데이터 수집 상태"""
    collection_id: Optional[str] = None
    source_type: Optional[DataSourceType] = None
    collection_config: Optional[CollectionConfig] = None
    collected_items: List[Dict[str, Any]] = []
    processed_items: List[ContentMetadata] = []
    failed_items: List[Dict[str, Any]] = []
    collection_status: CollectionStatus = CollectionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_items: int = 0
    success_count: int = 0
    error_count: int = 0

class DataCollectionAgent(BaseAgent[DataCollectionState]):
    """외부 데이터 수집 에이전트"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("data_collection", config)
        super().__init__("DataCollectionAgent", merged_config)
        self.agent_model_config = merged_config
        self.api_clients: Dict[DataSourceType, Any] = {}
        self.data_validator = DataValidator()
        self.content_processor = ContentProcessor()
        self._initialize_api_clients()

    def _initialize_api_clients(self) -> None:
        """API 클라이언트 초기화"""
        try:
            # 국가평생교육진흥원 API 클라이언트
            if self.config.get('nile_api_key'):
                self.api_clients[DataSourceType.NILE] = NileAPIClient(
                    api_key=self.config['nile_api_key'],
                    base_url=self.config.get('nile_base_url', 'https://api.nile.or.kr')
                )
            
            # 보건복지부 API 클라이언트
            if self.config.get('mohw_api_key'):
                self.api_clients[DataSourceType.MOHW] = MohwAPIClient(
                    api_key=self.config['mohw_api_key'],
                    base_url=self.config.get('mohw_base_url', 'https://api.mohw.go.kr')
                )
            
            # 육아정책연구소 API 클라이언트
            if self.config.get('kicce_api_key'):
                self.api_clients[DataSourceType.KICCE] = KicceAPIClient(
                    api_key=self.config['kicce_api_key'],
                    base_url=self.config.get('kicce_base_url', 'https://api.kicce.re.kr')
                )
                
        except Exception as e:
            self.logger.error(f"Failed to initialize API clients: {e}")

    async def execute(self, state: DataCollectionState) -> DataCollectionState:
        """데이터 수집 메인 실행 로직"""
        try:
            state = await self.pre_execute(state)
            state.start_time = datetime.now()
            state.collection_status = CollectionStatus.IN_PROGRESS
            
            # 1. 데이터 소스별 수집 실행
            state = await self._collect_data(state)
            
            # 2. 수집된 데이터 검증
            state = await self._validate_data(state)
            
            # 3. 콘텐츠 처리 및 메타데이터 생성
            state = await self._process_content(state)
            
            # 4. 데이터 저장
            state = await self._store_data(state)
            
            state.end_time = datetime.now()
            state.collection_status = CollectionStatus.COMPLETED
            
            state = await self.post_execute(state)
            
        except Exception as e:
            self.logger.error(f"Data collection failed: {e}")
            state.add_error(f"데이터 수집 실행 오류: {str(e)}")
            state.collection_status = CollectionStatus.FAILED
            state.end_time = datetime.now()
            
        return state

    async def _collect_data(self, state: DataCollectionState) -> DataCollectionState:
        """외부 API에서 데이터 수집"""
        try:
            if not state.source_type or state.source_type not in self.api_clients:
                raise ValueError(f"Unsupported data source: {state.source_type}")
            
            api_client = self.api_clients[state.source_type]
            
            # API별 수집 로직 실행
            if state.source_type == DataSourceType.NILE:
                state.collected_items = await self._collect_nile_data(api_client)
            elif state.source_type == DataSourceType.MOHW:
                state.collected_items = await self._collect_mohw_data(api_client)
            elif state.source_type == DataSourceType.KICCE:
                state.collected_items = await self._collect_kicce_data(api_client)
            
            state.total_items = len(state.collected_items)
            self.logger.info(f"Collected {state.total_items} items from {state.source_type.value}")
            
        except Exception as e:
            self.logger.error(f"Data collection failed: {e}")
            state.add_error(f"데이터 수집 실패: {str(e)}")
            
        return state

    async def _collect_nile_data(self, api_client) -> List[Dict[str, Any]]:
        """국가평생교육진흥원 데이터 수집"""
        try:
            # 연수과정 데이터 수집
            training_courses = await api_client.get_training_courses()
            
            # 강사정보 수집
            instructors = await api_client.get_instructors()
            
            # 기관정보 수집
            institutions = await api_client.get_institutions()
            
            # 데이터 통합
            collected_data = []
            collected_data.extend(training_courses)
            collected_data.extend(instructors)
            collected_data.extend(institutions)
            
            return collected_data
            
        except Exception as e:
            self.logger.error(f"NILE data collection failed: {e}")
            return []

    async def _collect_mohw_data(self, api_client) -> List[Dict[str, Any]]:
        """보건복지부 데이터 수집"""
        try:
            # 보육정책 데이터 수집
            policies = await api_client.get_childcare_policies()
            
            # 가이드라인 수집
            guidelines = await api_client.get_guidelines()
            
            # 법규 데이터 수집
            regulations = await api_client.get_regulations()
            
            # 데이터 통합
            collected_data = []
            collected_data.extend(policies)
            collected_data.extend(guidelines)
            collected_data.extend(regulations)
            
            return collected_data
            
        except Exception as e:
            self.logger.error(f"MOHW data collection failed: {e}")
            return []

    async def _collect_kicce_data(self, api_client) -> List[Dict[str, Any]]:
        """육아정책연구소 데이터 수집"""
        try:
            # 연구보고서 수집
            research_reports = await api_client.get_research_reports()
            
            # 통계자료 수집
            statistics = await api_client.get_statistics()
            
            # 정책분석 수집
            policy_analysis = await api_client.get_policy_analysis()
            
            # 데이터 통합
            collected_data = []
            collected_data.extend(research_reports)
            collected_data.extend(statistics)
            collected_data.extend(policy_analysis)
            
            return collected_data
            
        except Exception as e:
            self.logger.error(f"KICCE data collection failed: {e}")
            return []

    async def _validate_data(self, state: DataCollectionState) -> DataCollectionState:
        """수집된 데이터 검증"""
        try:
            validated_items = []
            failed_items = []
            
            for item in state.collected_items:
                try:
                    # 데이터 검증
                    if await self.data_validator.validate(item):
                        validated_items.append(item)
                    else:
                        failed_items.append({
                            'item': item,
                            'error': 'Validation failed'
                        })
                        
                except Exception as e:
                    failed_items.append({
                        'item': item,
                        'error': str(e)
                    })
            
            state.collected_items = validated_items
            state.failed_items = failed_items
            state.error_count = len(failed_items)
            
            self.logger.info(f"Validated {len(validated_items)} items, {len(failed_items)} failed")
            
        except Exception as e:
            self.logger.error(f"Data validation failed: {e}")
            state.add_error(f"데이터 검증 실패: {str(e)}")
            
        return state

    async def _process_content(self, state: DataCollectionState) -> DataCollectionState:
        """콘텐츠 처리 및 메타데이터 생성"""
        try:
            processed_items = []
            
            for item in state.collected_items:
                try:
                    # 콘텐츠 처리
                    processed_item = await self.content_processor.process(item)
                    
                    # 메타데이터 생성
                    metadata = await self._generate_metadata(processed_item)
                    
                    processed_items.append(metadata)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process item: {e}")
                    state.failed_items.append({
                        'item': item,
                        'error': str(e)
                    })
            
            state.processed_items = processed_items
            state.success_count = len(processed_items)
            
            self.logger.info(f"Processed {len(processed_items)} items")
            
        except Exception as e:
            self.logger.error(f"Content processing failed: {e}")
            state.add_error(f"콘텐츠 처리 실패: {str(e)}")
            
        return state

    async def _generate_metadata(self, item: Dict[str, Any]) -> ContentMetadata:
        """메타데이터 생성"""
        try:
            # ContentMetadata 스키마에 맞게 매핑
            metadata = ContentMetadata(
                id=item.get('id', ''),
                title=item.get('title', ''),
                content_type=self._determine_content_type(item),
                source=item.get('source', ''),
                url=item.get('file_url') or item.get('url') or None,
                description=item.get('summary') or item.get('description') or None,
                author=item.get('author') or None,
                created_at=item.get('created_at') or item.get('created_date') or datetime.now(),
                updated_at=item.get('updated_at') or item.get('updated_date') or datetime.now(),
                tags=item.get('tags') or item.get('keywords') or [],
                metadata={
                    'subject': item.get('subject'),
                    'difficulty_level': item.get('difficulty_level'),
                    'competency_area': item.get('competency_area'),
                    'learning_objectives': item.get('learning_objectives'),
                    'key_sentences': item.get('key_sentences'),
                    'file_size': item.get('file_size'),
                    'language': item.get('language'),
                    'institution': item.get('institution'),
                    'license': item.get('license'),
                    'version': item.get('version'),
                    'quality_score': item.get('quality_score'),
                    'completeness_score': item.get('completeness_score'),
                }
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata generation failed: {e}")
            raise

    def _determine_content_type(self, item: Dict[str, Any]) -> ContentType:
        """콘텐츠 유형 결정"""
        content_type = item.get('content_type', '').lower()
        
        if 'video' in content_type or 'mp4' in content_type:
            return ContentType.VIDEO
        elif 'document' in content_type or 'pdf' in content_type:
            return ContentType.DOCUMENT
        elif 'lecture' in content_type or 'course' in content_type:
            return ContentType.DOCUMENT
        elif 'interactive' in content_type or 'quiz' in content_type:
            return ContentType.INTERACTIVE
        elif 'audio' in content_type or 'mp3' in content_type:
            return ContentType.AUDIO
        elif 'image' in content_type or 'png' in content_type or 'jpg' in content_type:
            return ContentType.IMAGE
        else:
            return ContentType.OTHER

    async def _store_data(self, state: DataCollectionState) -> DataCollectionState:
        """데이터 저장"""
        try:
            # PostgreSQL에 메타데이터 저장
            await self._store_metadata(state.processed_items)
            
            # ChromaDB에 벡터 저장
            await self._store_vectors(state.processed_items)
            
            # 파일 저장 (필요한 경우)
            await self._store_files(state.processed_items)
            
            self.logger.info(f"Stored {len(state.processed_items)} items")
            
        except Exception as e:
            self.logger.error(f"Data storage failed: {e}")
            state.add_error(f"데이터 저장 실패: {str(e)}")
            
        return state

    async def _store_metadata(self, items: List[ContentMetadata]) -> None:
        """메타데이터를 PostgreSQL에 저장"""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from config.settings import get_settings

            settings = get_settings()
            database_url = settings.DATABASE_URL

            # SQLite인 경우 메모리에 저장
            if "sqlite" in database_url:
                self.logger.info(f"Using memory storage for {len(items)} metadata items")
                return

            sync_url = database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)

            # 테이블 생성 (없는 경우)
            from .persistence import ContentMetadataTable, Base
            Base.metadata.create_all(engine)

            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                for item in items:
                    db_item = ContentMetadataTable(
                        id=item.id,
                        title=item.title,
                        content_type=item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type),
                        source=item.source,
                        url=item.url,
                        description=item.description,
                        author=item.author,
                        created_at=item.created_at or datetime.now(),
                        updated_at=item.updated_at or datetime.now(),
                        tags=item.tags,
                        metadata_json=item.metadata
                    )
                    session.merge(db_item)  # upsert

                session.commit()
                self.logger.info(f"Stored {len(items)} metadata items to PostgreSQL")

            finally:
                session.close()
                engine.dispose()

        except ImportError as e:
            self.logger.warning(f"Persistence module not available: {e}")
        except Exception as e:
            self.logger.error(f"Failed to store metadata: {e}")
            raise

    async def _store_vectors(self, items: List[ContentMetadata]) -> None:
        """벡터를 ChromaDB에 저장"""
        try:
            from src.rag.retrieval_engine import RetrievalEngine

            # RetrievalEngine 초기화
            retrieval_engine = RetrievalEngine(self.config.get('retrieval', {}))

            # 문서 형식으로 변환
            documents = []
            for item in items:
                # 벡터 검색용 콘텐츠 생성
                content_parts = [item.title]
                if item.description:
                    content_parts.append(item.description)

                # 메타데이터에서 추가 콘텐츠 추출
                metadata = item.metadata or {}
                if metadata.get('learning_objectives'):
                    content_parts.append(str(metadata['learning_objectives']))
                if metadata.get('key_sentences'):
                    content_parts.append(str(metadata['key_sentences']))

                content = " ".join(content_parts)

                doc = {
                    'id': item.id,
                    'content': content,
                    'metadata': {
                        'title': item.title,
                        'content_type': item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type),
                        'source': item.source,
                        'url': item.url or '',
                        'author': item.author or '',
                        'tags': item.tags,
                        'created_at': item.created_at.isoformat() if item.created_at else datetime.now().isoformat(),
                    }
                }
                documents.append(doc)

            # ChromaDB에 추가
            success = await retrieval_engine.add_documents(documents)

            if success:
                self.logger.info(f"Stored {len(documents)} vectors to ChromaDB")
            else:
                self.logger.warning("Failed to store vectors to ChromaDB")

        except Exception as e:
            self.logger.error(f"Failed to store vectors: {e}")
            raise

    async def _store_files(self, items: List[ContentMetadata]) -> None:
        """파일을 로컬 스토리지에 저장"""
        try:
            import os
            import aiohttp
            from pathlib import Path

            # 저장 디렉토리 설정
            storage_dir = Path(self.config.get('storage_dir', './data/files'))
            storage_dir.mkdir(parents=True, exist_ok=True)

            stored_count = 0

            for item in items:
                # URL이 있는 경우에만 파일 다운로드
                if not item.url:
                    continue

                # 파일 확장자 결정
                content_type = item.content_type.value if hasattr(item.content_type, 'value') else str(item.content_type)
                ext_map = {
                    'document': '.pdf',
                    'video': '.mp4',
                    'audio': '.mp3',
                    'image': '.jpg',
                    'interactive': '.html',
                    'other': '.dat'
                }
                ext = ext_map.get(content_type, '.dat')

                # 파일 경로 생성
                file_path = storage_dir / f"{item.id}{ext}"

                # 이미 존재하면 스킵
                if file_path.exists():
                    continue

                # 파일 다운로드
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(item.url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                stored_count += 1
                                self.logger.debug(f"Downloaded file: {file_path}")
                            else:
                                self.logger.warning(f"Failed to download {item.url}: HTTP {response.status}")

                except Exception as e:
                    self.logger.warning(f"Failed to download file {item.url}: {e}")
                    continue

            self.logger.info(f"Stored {stored_count} files to {storage_dir}")

        except Exception as e:
            self.logger.error(f"Failed to store files: {e}")
            raise


# API 클라이언트 클래스들
import aiohttp
import asyncio
from urllib.parse import urlencode
import xml.etree.ElementTree as ET


class BaseAPIClient:
    """기본 API 클라이언트"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # API 키 추가
        if params is None:
            params = {}
        params['serviceKey'] = self.api_key

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                if method == "GET":
                    async with session.get(url, params=params) as response:
                        return await self._parse_response(response)
                else:
                    async with session.post(url, data=params) as response:
                        return await self._parse_response(response)

        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout: {url}")
            return {"error": "timeout", "items": []}
        except Exception as e:
            self.logger.error(f"Request failed: {url}, error: {e}")
            return {"error": str(e), "items": []}

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """응답 파싱 (XML/JSON 자동 감지)"""
        content_type = response.headers.get('Content-Type', '')
        text = await response.text()

        if response.status != 200:
            self.logger.error(f"API error: {response.status}, {text[:200]}")
            return {"error": f"HTTP {response.status}", "items": []}

        try:
            # JSON 응답
            if 'json' in content_type:
                import json
                data = json.loads(text)
                return self._normalize_response(data)

            # XML 응답 (공공데이터포털 기본 형식)
            elif 'xml' in content_type or text.strip().startswith('<?xml'):
                return self._parse_xml_response(text)

            # 기본적으로 JSON 시도
            else:
                import json
                try:
                    data = json.loads(text)
                    return self._normalize_response(data)
                except json.JSONDecodeError:
                    return self._parse_xml_response(text)

        except Exception as e:
            self.logger.error(f"Response parsing failed: {e}")
            return {"error": str(e), "items": []}

    def _parse_xml_response(self, xml_text: str) -> Dict[str, Any]:
        """XML 응답 파싱 (공공데이터포털 표준 형식)"""
        try:
            root = ET.fromstring(xml_text)

            # 에러 체크
            result_code = root.findtext('.//resultCode') or root.findtext('.//header/resultCode')
            if result_code and result_code != '00':
                error_msg = root.findtext('.//resultMsg') or root.findtext('.//header/resultMsg')
                return {"error": error_msg, "items": []}

            # 아이템 추출
            items = []
            for item in root.findall('.//item'):
                item_dict = {}
                for child in item:
                    item_dict[child.tag] = child.text
                items.append(item_dict)

            # 페이지 정보
            total_count = root.findtext('.//totalCount') or '0'

            return {
                "items": items,
                "totalCount": int(total_count),
                "error": None
            }

        except ET.ParseError as e:
            self.logger.error(f"XML parsing failed: {e}")
            return {"error": str(e), "items": []}

    def _normalize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """응답 정규화"""
        # 공공데이터포털 표준 응답 구조
        if 'response' in data:
            body = data['response'].get('body', {})
            items = body.get('items', {})

            if isinstance(items, dict):
                item_list = items.get('item', [])
            else:
                item_list = items if isinstance(items, list) else []

            # 단일 아이템인 경우 리스트로 변환
            if isinstance(item_list, dict):
                item_list = [item_list]

            return {
                "items": item_list,
                "totalCount": body.get('totalCount', len(item_list)),
                "error": None
            }

        # 이미 정규화된 형식
        if 'items' in data:
            return data

        # 배열 직접 반환
        if isinstance(data, list):
            return {"items": data, "totalCount": len(data), "error": None}

        return {"items": [], "totalCount": 0, "error": None}


class NileAPIClient(BaseAPIClient):
    """국가평생교육진흥원 API 클라이언트

    국가평생교육진흥원의 공공데이터를 수집합니다.
    - 연수과정: 교사 연수 프로그램 정보
    - 강사정보: 연수 강사 데이터
    - 기관정보: 교육기관 정��
    """

    async def get_training_courses(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """연수과정 데이터 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/trainingCourse/list', params)

            if result.get('error'):
                self.logger.warning(f"Training courses API error: {result['error']}")
                return []

            items = result.get('items', [])

            # 데이터 정규화
            normalized = []
            for item in items:
                normalized.append({
                    'id': f"nile_course_{item.get('courseId', '')}",
                    'title': item.get('courseName', item.get('title', '')),
                    'description': item.get('courseDesc', item.get('description', '')),
                    'content_type': 'course',
                    'source': 'NILE',
                    'url': item.get('courseUrl', ''),
                    'author': item.get('instructorName', ''),
                    'tags': self._extract_tags(item),
                    'metadata': {
                        'course_id': item.get('courseId'),
                        'duration': item.get('duration'),
                        'credit': item.get('credit'),
                        'target_audience': item.get('targetAudience'),
                        'category': item.get('category'),
                        'start_date': item.get('startDate'),
                        'end_date': item.get('endDate'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} training courses from NILE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get training courses: {e}")
            return []

    async def get_instructors(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """강사정보 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/instructor/list', params)

            if result.get('error'):
                self.logger.warning(f"Instructors API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"nile_instructor_{item.get('instructorId', '')}",
                    'title': item.get('instructorName', ''),
                    'description': item.get('profile', item.get('introduction', '')),
                    'content_type': 'instructor',
                    'source': 'NILE',
                    'author': item.get('instructorName', ''),
                    'tags': item.get('specialties', '').split(',') if item.get('specialties') else [],
                    'metadata': {
                        'instructor_id': item.get('instructorId'),
                        'affiliation': item.get('affiliation'),
                        'expertise': item.get('expertise'),
                        'career': item.get('career'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} instructors from NILE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get instructors: {e}")
            return []

    async def get_institutions(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """기관정보 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/institution/list', params)

            if result.get('error'):
                self.logger.warning(f"Institutions API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"nile_institution_{item.get('institutionId', '')}",
                    'title': item.get('institutionName', ''),
                    'description': item.get('introduction', ''),
                    'content_type': 'institution',
                    'source': 'NILE',
                    'url': item.get('homepage', ''),
                    'tags': [],
                    'metadata': {
                        'institution_id': item.get('institutionId'),
                        'address': item.get('address'),
                        'phone': item.get('phone'),
                        'type': item.get('institutionType'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} institutions from NILE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get institutions: {e}")
            return []

    def _extract_tags(self, item: Dict[str, Any]) -> List[str]:
        """아이템에서 태그 추출"""
        tags = []
        if item.get('category'):
            tags.append(item['category'])
        if item.get('subject'):
            tags.append(item['subject'])
        if item.get('keywords'):
            tags.extend(item['keywords'].split(','))
        return [t.strip() for t in tags if t.strip()]


class MohwAPIClient(BaseAPIClient):
    """보건복지부 API 클라이언트

    보건복지부의 공공데이터를 수집합니다.
    - 보육정책: 보육 관련 정책 정보
    - 가이드라인: 시설 운영 가이드라인
    - 법규: 관련 법령 및 규정
    """

    async def get_childcare_policies(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """보육정책 데이터 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/childcare/policy/list', params)

            if result.get('error'):
                self.logger.warning(f"Childcare policies API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"mohw_policy_{item.get('policyId', item.get('id', ''))}",
                    'title': item.get('policyName', item.get('title', '')),
                    'description': item.get('policyDesc', item.get('content', '')),
                    'content_type': 'policy',
                    'source': 'MOHW',
                    'url': item.get('detailUrl', ''),
                    'author': item.get('department', '보건복지부'),
                    'tags': self._extract_policy_tags(item),
                    'metadata': {
                        'policy_id': item.get('policyId'),
                        'effective_date': item.get('effectiveDate'),
                        'department': item.get('department'),
                        'target': item.get('target'),
                        'budget': item.get('budget'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} childcare policies from MOHW")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get childcare policies: {e}")
            return []

    async def get_guidelines(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """가이드라인 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/childcare/guideline/list', params)

            if result.get('error'):
                self.logger.warning(f"Guidelines API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"mohw_guideline_{item.get('guidelineId', item.get('id', ''))}",
                    'title': item.get('guidelineName', item.get('title', '')),
                    'description': item.get('content', item.get('summary', '')),
                    'content_type': 'guideline',
                    'source': 'MOHW',
                    'url': item.get('fileUrl', ''),
                    'author': item.get('department', '보건복지부'),
                    'tags': ['가이드라인', item.get('category', '')],
                    'metadata': {
                        'guideline_id': item.get('guidelineId'),
                        'version': item.get('version'),
                        'publish_date': item.get('publishDate'),
                        'file_size': item.get('fileSize'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} guidelines from MOHW")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get guidelines: {e}")
            return []

    async def get_regulations(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """법규 데이터 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/childcare/regulation/list', params)

            if result.get('error'):
                self.logger.warning(f"Regulations API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"mohw_regulation_{item.get('regulationId', item.get('id', ''))}",
                    'title': item.get('regulationName', item.get('title', '')),
                    'description': item.get('content', item.get('summary', '')),
                    'content_type': 'regulation',
                    'source': 'MOHW',
                    'url': item.get('detailUrl', ''),
                    'author': '보건복지부',
                    'tags': ['법규', '규정'],
                    'metadata': {
                        'regulation_id': item.get('regulationId'),
                        'regulation_number': item.get('regulationNumber'),
                        'enforcement_date': item.get('enforcementDate'),
                        'revision_date': item.get('revisionDate'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} regulations from MOHW")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get regulations: {e}")
            return []

    def _extract_policy_tags(self, item: Dict[str, Any]) -> List[str]:
        """정책에서 태그 추출"""
        tags = ['정책']
        if item.get('category'):
            tags.append(item['category'])
        if item.get('target'):
            tags.append(item['target'])
        return tags


class KicceAPIClient(BaseAPIClient):
    """육아정책연구소 API 클라이언트

    육아정책연구소의 공공데이터를 수집합니다.
    - 연구보고서: 연구 결과물
    - 통계자료: 보육 관련 통계
    - 정책분석: 정책 분석 자료
    """

    async def get_research_reports(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """연구보고서 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/research/report/list', params)

            if result.get('error'):
                self.logger.warning(f"Research reports API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"kicce_report_{item.get('reportId', item.get('id', ''))}",
                    'title': item.get('reportName', item.get('title', '')),
                    'description': item.get('abstract', item.get('summary', '')),
                    'content_type': 'research_report',
                    'source': 'KICCE',
                    'url': item.get('fileUrl', item.get('pdfUrl', '')),
                    'author': item.get('author', item.get('researcher', '')),
                    'tags': self._extract_research_tags(item),
                    'metadata': {
                        'report_id': item.get('reportId'),
                        'report_type': item.get('reportType'),
                        'publish_year': item.get('publishYear'),
                        'pages': item.get('pages'),
                        'keywords': item.get('keywords'),
                        'doi': item.get('doi'),
                    },
                    'created_at': item.get('publishDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} research reports from KICCE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get research reports: {e}")
            return []

    async def get_statistics(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """통계자료 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/statistics/list', params)

            if result.get('error'):
                self.logger.warning(f"Statistics API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"kicce_stat_{item.get('statId', item.get('id', ''))}",
                    'title': item.get('statName', item.get('title', '')),
                    'description': item.get('description', ''),
                    'content_type': 'statistics',
                    'source': 'KICCE',
                    'url': item.get('dataUrl', ''),
                    'author': '육아정책연구소',
                    'tags': ['통계', item.get('category', '')],
                    'metadata': {
                        'stat_id': item.get('statId'),
                        'stat_year': item.get('statYear'),
                        'data_period': item.get('dataPeriod'),
                        'unit': item.get('unit'),
                        'source': item.get('dataSource'),
                    },
                    'created_at': item.get('regDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} statistics from KICCE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return []

    async def get_policy_analysis(self, page: int = 1, per_page: int = 100) -> List[Dict[str, Any]]:
        """정책분석 수집"""
        try:
            params = {
                'pageNo': page,
                'numOfRows': per_page,
                'type': 'json'
            }

            result = await self._request('/openapi/policy/analysis/list', params)

            if result.get('error'):
                self.logger.warning(f"Policy analysis API error: {result['error']}")
                return []

            items = result.get('items', [])

            normalized = []
            for item in items:
                normalized.append({
                    'id': f"kicce_analysis_{item.get('analysisId', item.get('id', ''))}",
                    'title': item.get('analysisName', item.get('title', '')),
                    'description': item.get('summary', item.get('content', '')),
                    'content_type': 'policy_analysis',
                    'source': 'KICCE',
                    'url': item.get('fileUrl', ''),
                    'author': item.get('author', '육아정책연구소'),
                    'tags': ['정책분석', item.get('policyArea', '')],
                    'metadata': {
                        'analysis_id': item.get('analysisId'),
                        'policy_area': item.get('policyArea'),
                        'analysis_method': item.get('analysisMethod'),
                        'implications': item.get('implications'),
                    },
                    'created_at': item.get('publishDate', datetime.now().isoformat()),
                })

            self.logger.info(f"Collected {len(normalized)} policy analyses from KICCE")
            return normalized

        except Exception as e:
            self.logger.error(f"Failed to get policy analysis: {e}")
            return []

    def _extract_research_tags(self, item: Dict[str, Any]) -> List[str]:
        """연구보고서에서 태그 추출"""
        tags = ['연구보고서']
        if item.get('reportType'):
            tags.append(item['reportType'])
        if item.get('keywords'):
            keywords = item['keywords']
            if isinstance(keywords, str):
                tags.extend([k.strip() for k in keywords.split(',')])
            elif isinstance(keywords, list):
                tags.extend(keywords)
        return [t for t in tags if t]


# 유틸리티 클래스들
class DataValidator:
    """데이터 검증기

    수집된 데이터의 품질과 무결성을 검증합니다.
    """

    def __init__(self):
        self.logger = logging.getLogger("DataValidator")
        self.required_fields = ['id', 'title', 'source']
        self.max_title_length = 500
        self.max_description_length = 10000

    async def validate(self, item: Dict[str, Any]) -> bool:
        """데이터 검증

        Args:
            item: 검증할 데이터 아이템

        Returns:
            검증 통과 여부
        """
        try:
            # 1. 필수 필드 검증
            for field in self.required_fields:
                if not item.get(field):
                    self.logger.warning(f"Missing required field: {field}")
                    return False

            # 2. ID 형식 검증
            item_id = str(item.get('id', ''))
            if not item_id or len(item_id) > 255:
                self.logger.warning(f"Invalid ID format: {item_id[:50]}")
                return False

            # 3. 제목 검증
            title = str(item.get('title', ''))
            if not title.strip():
                self.logger.warning("Empty title")
                return False
            if len(title) > self.max_title_length:
                self.logger.warning(f"Title too long: {len(title)} chars")
                return False

            # 4. 설명 길이 검증
            description = item.get('description', '') or ''
            if len(str(description)) > self.max_description_length:
                self.logger.warning(f"Description too long: {len(str(description))} chars")
                return False

            # 5. URL 검증 (있는 경우)
            url = item.get('url', '')
            if url and not self._is_valid_url(str(url)):
                self.logger.warning(f"Invalid URL format: {url[:100]}")
                # URL이 잘못되어도 실패하지 않음 (경고만)

            # 6. 소스 검증
            source = str(item.get('source', '')).upper()
            valid_sources = ['NILE', 'MOHW', 'KICCE', 'MANUAL']
            if source not in valid_sources:
                self.logger.warning(f"Unknown source: {source}")
                # 알 수 없는 소스도 허용 (확장성)

            # 7. 날짜 형식 검증
            created_at = item.get('created_at')
            if created_at and isinstance(created_at, str):
                if not self._is_valid_date(created_at):
                    self.logger.warning(f"Invalid date format: {created_at}")
                    # 날짜가 잘못되어도 실패하지 않음

            # 8. 중복 콘텐츠 감지 (제목 기반)
            # TODO: 실제로는 데이터베이스 조회 필요

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    def _is_valid_url(self, url: str) -> bool:
        """URL 형식 검증"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))

    def _is_valid_date(self, date_str: str) -> bool:
        """날짜 형식 검증"""
        from datetime import datetime
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y%m%d',
        ]
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        return False


class ContentProcessor:
    """콘텐츠 처리기

    수집된 데이터를 정제하고 향상시킵니다.
    """

    def __init__(self):
        self.logger = logging.getLogger("ContentProcessor")

    async def process(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """콘텐츠 처리

        Args:
            item: 처리할 데이터 아이템

        Returns:
            처리된 데이터 아이템
        """
        try:
            processed = item.copy()

            # 1. 텍스트 정제
            processed = self._clean_text_fields(processed)

            # 2. 날짜 정규화
            processed = self._normalize_dates(processed)

            # 3. 태그 정제
            processed = self._clean_tags(processed)

            # 4. 품질 점수 계산
            processed['quality_score'] = self._calculate_quality_score(processed)

            # 5. 완성도 점수 계산
            processed['completeness_score'] = self._calculate_completeness_score(processed)

            # 6. 키워드 추출
            processed['extracted_keywords'] = self._extract_keywords(processed)

            # 7. 핵심 문장 추출
            processed['key_sentences'] = self._extract_key_sentences(processed)

            return processed

        except Exception as e:
            self.logger.error(f"Content processing error: {e}")
            return item  # 실패 시 원본 반환

    def _clean_text_fields(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 필드 정제"""
        import re

        text_fields = ['title', 'description', 'author']

        for field in text_fields:
            if field in item and item[field]:
                text = str(item[field])
                # HTML 태그 제거
                text = re.sub(r'<[^>]+>', '', text)
                # 연속된 공백 제거
                text = re.sub(r'\s+', ' ', text)
                # 앞뒤 공백 제거
                text = text.strip()
                item[field] = text

        return item

    def _normalize_dates(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """날짜 정규화"""
        from datetime import datetime

        date_fields = ['created_at', 'updated_at']

        for field in date_fields:
            if field in item and item[field]:
                value = item[field]

                # 이미 datetime인 경우
                if isinstance(value, datetime):
                    continue

                # 문자열인 경우 파싱 시도
                if isinstance(value, str):
                    parsed = self._parse_date(value)
                    if parsed:
                        item[field] = parsed
                    else:
                        item[field] = datetime.now()

        return item

    def _parse_date(self, date_str: str):
        """날짜 문자열 파싱"""
        from datetime import datetime

        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y%m%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _clean_tags(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """태그 정제"""
        if 'tags' in item and item['tags']:
            tags = item['tags']
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',')]

            # 정제된 태그
            cleaned_tags = []
            for tag in tags:
                tag = str(tag).strip().lower()
                if tag and len(tag) <= 50:  # 태그 길이 제한
                    cleaned_tags.append(tag)

            # 중복 제거
            item['tags'] = list(set(cleaned_tags))

        return item

    def _calculate_quality_score(self, item: Dict[str, Any]) -> float:
        """품질 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0

        # 제목 품질 (0.2)
        title = item.get('title', '')
        if title:
            if len(title) >= 10:
                score += 0.1
            if len(title) >= 20:
                score += 0.1

        # 설명 품질 (0.3)
        description = item.get('description', '')
        if description:
            desc_len = len(str(description))
            if desc_len >= 50:
                score += 0.1
            if desc_len >= 100:
                score += 0.1
            if desc_len >= 200:
                score += 0.1

        # URL 존재 (0.1)
        if item.get('url'):
            score += 0.1

        # 작성자 존재 (0.1)
        if item.get('author'):
            score += 0.1

        # 태그 존재 (0.2)
        tags = item.get('tags', [])
        if tags:
            if len(tags) >= 1:
                score += 0.1
            if len(tags) >= 3:
                score += 0.1

        # 메타데이터 풍부도 (0.1)
        metadata = item.get('metadata', {})
        if metadata and len(metadata) >= 3:
            score += 0.1

        return round(min(score, 1.0), 2)

    def _calculate_completeness_score(self, item: Dict[str, Any]) -> float:
        """완성도 점수 계산 (0.0 ~ 1.0)"""
        fields = ['id', 'title', 'description', 'content_type', 'source', 'url', 'author', 'tags', 'created_at']
        filled = sum(1 for f in fields if item.get(f))
        return round(filled / len(fields), 2)

    def _extract_keywords(self, item: Dict[str, Any]) -> List[str]:
        """키워드 추출"""
        import re

        text_parts = []
        if item.get('title'):
            text_parts.append(str(item['title']))
        if item.get('description'):
            text_parts.append(str(item['description'])[:500])

        if not text_parts:
            return []

        text = ' '.join(text_parts)

        # 간단한 키워드 추출 (불용어 제거 후 빈도 기반)
        # 실제로는 더 정교한 NLP 필요
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                    'up', 'about', 'into', 'over', 'after', 'and', 'or', 'but',
                    '및', '등', '의', '을', '를', '이', '가', '에', '은', '는'}

        # 단어 추출
        words = re.findall(r'\b[a-zA-Z가-힣]{2,}\b', text.lower())
        words = [w for w in words if w not in stopwords]

        # 빈도 계산
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 상위 10개 키워드
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:10]]

    def _extract_key_sentences(self, item: Dict[str, Any]) -> List[str]:
        """핵심 문장 추출"""
        description = item.get('description', '')
        if not description:
            return []

        # 문장 분리
        import re
        sentences = re.split(r'[.!?。]\s*', str(description))
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 20]

        # 처음 3문장 반환
        return sentences[:3]


