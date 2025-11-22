"""문서 처리 및 전처리"""

# type: ignore
import re
import json
import logging
from typing import Dict, Any, List, Optional, cast
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """문서 처리 및 전처리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("DocumentProcessor")
        
        # 처리 설정
        self.max_chunk_size = self.config.get('max_chunk_size', 1000)
        self.chunk_overlap = self.config.get('chunk_overlap', 200)
        self.min_chunk_size = self.config.get('min_chunk_size', 100)
        # 멀티모달 전처리 플러그인 설정
        self.enable_ocr = self.config.get('enable_ocr', False)
        self.ocr_lang = self.config.get('ocr_lang', 'kor+eng')
        # OCR 엔진 경로/데이터셋 설정
        try:
            from config.settings import get_settings
            st = get_settings()
            self.tesseract_cmd = st.TESSERACT_CMD
            self.tessdata_prefix = st.TESSDATA_PREFIX
            self.ocr_clean_filters = [s for s in (st.OCR_CLEAN_FILTERS.split(',') if st.OCR_CLEAN_FILTERS else [])]
        except Exception:
            self.tesseract_cmd = ""
            self.tessdata_prefix = ""
            self.ocr_clean_filters = ['\t', '\n', '\r']
        
        # 텍스트 정제 설정
        self.remove_special_chars = self.config.get('remove_special_chars', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.remove_duplicates = self.config.get('remove_duplicates', True)
    
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """문서 전처리"""
        try:
            # 기본 정보 추출
            doc_id = document.get('id', self._generate_doc_id(document))
            content = document.get('content', '')
            metadata = document.get('metadata', {})

            # OCR/비전 전처리: 이미지/스캔 문서에서 텍스트 추출
            if self.enable_ocr and not content:
                ocr_text = await self._try_ocr(document)
                if ocr_text:
                    content = ocr_text
            
            # 텍스트 정제
            cleaned_content = await self._clean_text(content)
            
            # 청크 분할
            chunks = await self._split_into_chunks(cleaned_content)
            
            # 메타데이터 강화
            enhanced_metadata = await self._enhance_metadata(metadata, cleaned_content)
            
            # 처리된 문서 반환
            processed_doc = {
                'id': doc_id,
                'content': cleaned_content,
                'chunks': chunks,
                'metadata': enhanced_metadata,
                'processed_at': datetime.now().isoformat(),
                'processing_stats': {
                    'original_length': len(content),
                    'cleaned_length': len(cleaned_content),
                    'num_chunks': len(chunks),
                    'avg_chunk_size': sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
                }
            }
            
            return processed_doc
            
        except Exception as e:
            self.logger.error(f"Document processing failed: {e}")
            return document
    
    async def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        try:
            if not text:
                return ""
            
            # 1. 기본 정제
            cleaned = text.strip()
            
            # 2. 특수 문자 제거 (선택적)
            if self.remove_special_chars:
                # 유지할 특수 문자: 한글, 영문, 숫자, 기본 구두점
                cleaned = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]', ' ', cleaned)
            
            # 3. 공백 정규화
            if self.normalize_whitespace:
                cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # 4. 중복 문장 제거 (선택적)
            if self.remove_duplicates:
                cleaned = await self._remove_duplicate_sentences(cleaned)
            
            # 5. 최종 정제
            cleaned = cleaned.strip()
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Text cleaning failed: {e}")
            return text
    
    async def _split_into_chunks(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        try:
            if not text or len(text) <= self.max_chunk_size:
                return [text] if text else []
            
            chunks = []
            start = 0
            
            while start < len(text):
                # 청크 끝 위치 계산
                end = min(start + self.max_chunk_size, len(text))
                
                # 문장 경계에서 분할 시도
                if end < len(text):
                    # 마지막 문장 끝 찾기
                    last_sentence_end = text.rfind('.', start, end)
                    if last_sentence_end > start + self.min_chunk_size:
                        end = last_sentence_end + 1
                
                chunk = text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                
                # 다음 청크 시작 위치 (오버랩 고려)
                start = end - self.chunk_overlap
                if start >= len(text):
                    break
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Text chunking failed: {e}")
            return [text] if text else []
    
    async def _enhance_metadata(self, metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
        """메타데이터 강화"""
        try:
            enhanced = metadata.copy()
            
            # 기본 정보 추가
            enhanced.update({
                'content_length': len(content),
                'word_count': len(content.split()),
                'processed_at': datetime.now().isoformat()
            })
            
            # 키워드 추출
            keywords = await self._extract_keywords(content)
            if keywords:
                enhanced['keywords'] = keywords
            
            # 카테고리 분류
            category = await self._classify_content(content)
            if category:
                enhanced['category'] = category
            
            # 언어 감지
            language = await self._detect_language(content)
            if language:
                enhanced['language'] = language
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Metadata enhancement failed: {e}")
            return metadata
    
    async def _remove_duplicate_sentences(self, text: str) -> str:
        """중복 문장 제거"""
        try:
            sentences = text.split('.')
            unique_sentences = []
            seen = set()
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in seen:
                    seen.add(sentence)
                    unique_sentences.append(sentence)
            
            return '. '.join(unique_sentences)
            
        except Exception as e:
            self.logger.error(f"Duplicate sentence removal failed: {e}")
            return text
    
    async def _extract_keywords(self, content: str) -> List[str]:
        """키워드 추출"""
        try:
            # 간단한 키워드 추출 (실제로는 더 정교한 NLP 기법 사용)
            words = re.findall(r'\b\w+\b', content.lower())
            
            # 불용어 제거
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                '이', '그', '저', '의', '을', '를', '에', '에서', '로', '으로', '와', '과', '는', '은'
            }
            
            filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            # 빈도 계산
            word_freq: Dict[str, int] = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # 상위 키워드 선택
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return [word for word, freq in keywords if freq > 1]
            
        except Exception as e:
            self.logger.error(f"Keyword extraction failed: {e}")
            return []
    
    async def _classify_content(self, content: str) -> Optional[str]:
        """콘텐츠 카테고리 분류"""
        try:
            # 간단한 키워드 기반 분류
            content_lower = content.lower()
            
            # 육아 관련 키워드
            parenting_keywords = ['육아', '아이', '아동', '부모', '양육', '발달', '교육']
            if any(keyword in content_lower for keyword in parenting_keywords):
                return 'parenting'
            
            # 정책 관련 키워드
            policy_keywords = ['정책', '제도', '법률', '규정', '지원', '혜택']
            if any(keyword in content_lower for keyword in policy_keywords):
                return 'policy'
            
            # 교육 관련 키워드
            education_keywords = ['교육', '학습', '훈련', '과정', '프로그램']
            if any(keyword in content_lower for keyword in education_keywords):
                return 'education'
            
            # 건강 관련 키워드
            health_keywords = ['건강', '의료', '질병', '예방', '치료']
            if any(keyword in content_lower for keyword in health_keywords):
                return 'health'
            
            return 'general'
            
        except Exception as e:
            self.logger.error(f"Content classification failed: {e}")
            return None
    
    async def _detect_language(self, content: str) -> Optional[str]:
        """언어 감지"""
        try:
            # 간단한 언어 감지
            korean_chars = len(re.findall(r'[가-힣]', content))
            english_chars = len(re.findall(r'[a-zA-Z]', content))
            
            if korean_chars > english_chars:
                return 'ko'
            elif english_chars > korean_chars:
                return 'en'
            else:
                return 'mixed'
                
        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            return None
    
    def _generate_doc_id(self, document: Dict[str, Any]) -> str:
        """문서 ID 생성"""
        try:
            content = document.get('content', '')
            metadata = document.get('metadata', {})
            
            # 내용과 메타데이터를 기반으로 해시 생성
            combined = f"{content}{json.dumps(metadata, sort_keys=True)}"
            doc_hash = hashlib.md5(combined.encode()).hexdigest()[:12]
            
            return f"doc_{doc_hash}"
            
        except Exception as e:
            self.logger.error(f"Document ID generation failed: {e}")
            return f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def batch_process_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문서 배치 처리"""
        try:
            processed_docs = []
            
            for doc in documents:
                processed_doc = await self.process_document(doc)
                processed_docs.append(processed_doc)
            
            return processed_docs
            
        except Exception as e:
            self.logger.error(f"Batch document processing failed: {e}")
            return documents

    async def _try_ocr(self, document: Dict[str, Any]) -> str:
        """가능하면 OCR 시도(선택적, 의존성 없으면 건너뜀)."""
        try:
            file_path = document.get('file_path') or document.get('image_path')
            if not file_path:
                return ""
            try:
                from PIL import Image  # type: ignore
                import pytesseract  # type: ignore
            except Exception:
                return ""
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            if self.tessdata_prefix:
                import os
                os.environ['TESSDATA_PREFIX'] = self.tessdata_prefix
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang=self.ocr_lang)
            cleaned = text
            for f in self.ocr_clean_filters:
                cleaned = cleaned.replace(f, ' ')
            return cleaned.strip()
        except Exception:
            return ""
    
    async def create_document_index(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:  # type: ignore
        """문서 인덱스 생성"""
        try:
            index: Dict[str, Any] = {
                'total_documents': len(documents),
                'categories': {},
                'keywords': {},
                'languages': {},
                'created_at': datetime.now().isoformat()
            }
            
            for doc in documents:
                metadata = doc.get('metadata', {})
                if not isinstance(metadata, dict):
                    continue
                
                # 타입 캐스팅으로 mypy 경고 해결
                categories_dict = cast(Dict[str, int], index['categories'])  # type: ignore
                keywords_dict = cast(Dict[str, int], index['keywords'])  # type: ignore
                languages_dict = cast(Dict[str, int], index['languages'])  # type: ignore
                
                # 카테고리별 분류
                category = metadata.get('category', 'unknown')
                if isinstance(category, str):
                    if category not in categories_dict:  # type: ignore
                        categories_dict[category] = 0  # type: ignore
                    categories_dict[category] += 1  # type: ignore
                
                # 키워드 수집
                keywords = metadata.get('keywords', [])
                if isinstance(keywords, list):
                    for keyword in keywords:
                        if isinstance(keyword, str):
                            if keyword not in keywords_dict:  # type: ignore
                                keywords_dict[keyword] = 0  # type: ignore
                            keywords_dict[keyword] += 1  # type: ignore
                
                # 언어별 분류
                language = metadata.get('language', 'unknown')
                if isinstance(language, str):
                    if language not in languages_dict:  # type: ignore
                        languages_dict[language] = 0  # type: ignore
                    languages_dict[language] += 1  # type: ignore
            
            return index
            
        except Exception as e:
            self.logger.error(f"Document index creation failed: {e}")
            return {'total_documents': 0, 'error': str(e)}
