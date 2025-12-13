"""RAG 시스템용 프롬프트 템플릿 (마크다운 파일 기반)"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """프롬프트 타입"""

    COMPETENCY_ASSESSMENT = "competency_assessment"
    RECOMMENDATION = "recommendation"
    SEARCH = "search"
    ANALYTICS = "analytics"
    GENERAL_CHAT = "general_chat"
    DATA_COLLECTION = "data_collection"


class PromptTemplates:
    """
    RAG 시스템용 프롬프트 템플릿 관리

    마크다운 파일 기반 프롬프트 로딩:
    - src/agents/{agent_name}/prompts/system.md
    - src/agents/{agent_name}/prompts/{action}.md

    하위 호환성을 위해 기존 인터페이스 유지
    """

    def __init__(self):
        self.prompt_loader = get_prompt_loader()

        # 하위 호환성을 위한 fallback 템플릿 (마크다운 파일이 없을 경우)
        self.templates = self._initialize_templates()
        self.system_prompts = self._initialize_system_prompts()

        # 이름 기반 매핑
        self._name_to_type = {
            "competency_assessment": PromptType.COMPETENCY_ASSESSMENT,
            "recommendation": PromptType.RECOMMENDATION,
            "search": PromptType.SEARCH,
            "analytics": PromptType.ANALYTICS,
            "general_chat": PromptType.GENERAL_CHAT,
            "data_collection": PromptType.DATA_COLLECTION,
        }

        # 타입별 에이전트 매핑
        self._type_to_agent = {
            PromptType.COMPETENCY_ASSESSMENT: "competency_agent",
            PromptType.RECOMMENDATION: "recommendation_agent",
            PromptType.SEARCH: "search_agent",
            PromptType.ANALYTICS: "analytics_agent",
            PromptType.GENERAL_CHAT: "creator_onboarding_agent",
            PromptType.DATA_COLLECTION: "data_collection_agent",
        }

        self._rag_answer_template = (
            "You are a helpful assistant. Using the provided context, answer the question.\n"
            "If the answer is not in the context, say you don't know.\n\n"
            "Context:\n{context}\n\nQuestion: {question}"
        )

    def _initialize_templates(self) -> Dict[PromptType, str]:
        """프롬프트 템플릿 초기화"""
        return {
            PromptType.COMPETENCY_ASSESSMENT: """
당신은 전문적인 역량진단 AI 어시스턴트입니다.

**역할**: 사용자의 응답을 분석하여 개인별 역량 수준을 진단하고 맞춤형 학습 방향을 제시합니다.

**분석 기준**:
- 응답의 깊이와 정확성
- 실무 적용 가능성
- 전문성 수준
- 학습 성장 잠재력

**진단 결과 형식**:
1. 역량 점수 (0-100점)
2. 역량 수준 (기초/중급/고급)
3. 강점 영역
4. 개선 필요 영역
5. 맞춤형 학습 추천

**사용자 응답**: {user_responses}

**기존 역량 데이터**: {competency_data}

**맥락 정보**: {context}

위 정보를 바탕으로 종합적인 역량진단을 수행해주세요.
""",
            PromptType.RECOMMENDATION: """
당신은 개인화된 학습 추천 AI 어시스턴트입니다.

**역할**: 사용자의 역량 수준, 학습 선호도, 관심사를 종합하여 최적의 학습 자료를 추천합니다.

**추천 기준**:
- 사용자 역량 수준에 맞는 난이도
- 학습 스타일과 선호도
- 관심사와 목표
- 학습 자료의 품질과 평점

**사용자 프로필**:
- 역량 수준: {competency_level}
- 학습 선호도: {learning_preferences}
- 관심사: {interests}
- 학습 목표: {learning_goals}

**추천 결과 형식**:
1. 추천 학습 자료 (3-5개)
2. 각 자료의 추천 이유
3. 학습 순서 제안
4. 예상 학습 시간
5. 추가 학습 경로

**검색된 관련 자료**: {retrieved_documents}

위 정보를 바탕으로 개인화된 학습 추천을 제공해주세요.
""",
            PromptType.SEARCH: """
당신은 지능형 검색 AI 어시스턴트입니다.

**역할**: 사용자의 검색 의도를 이해하고 관련성 높은 정보를 제공합니다.

**검색 쿼리**: {query}
**검색 필터**: {filters}
**검색 결과**: {search_results}

**응답 형식**:
1. 검색 결과 요약
2. 핵심 정보 추출
3. 관련 추가 자료 제안
4. 검색 결과의 신뢰도 평가

위 검색 결과를 바탕으로 사용자에게 유용한 정보를 제공해주세요.
""",
            PromptType.ANALYTICS: """
당신은 데이터 분석 전문가입니다.

**역할**: 학습 데이터를 분석하여 인사이트와 개선 방안을 제시합니다.

**분석 요청**: {report_type}
**분석 기간**: {date_range}
**분석 데이터**: {analytics_data}
**사용자 데이터**: {user_data}

**분석 결과 형식**:
1. 핵심 지표 요약
2. 트렌드 분석
3. 성과 요인 분석
4. 개선 제안사항
5. 향후 학습 방향

위 데이터를 바탕으로 종합적인 분석 리포트를 작성해주세요.
""",
            PromptType.GENERAL_CHAT: """
당신은 육아정책연구소의 디지털연수 특화 AI 어시스턴트입니다.

**역할**: 육아, 교육, 정책 관련 질문에 대해 전문적이고 도움이 되는 답변을 제공합니다.

**대화 맥락**:
- 사용자: {user_id}
- 세션: {session_id}
- 이전 대화: {conversation_history}

**검색된 관련 정보**: {retrieved_context}

**응답 가이드라인**:
1. 정확하고 신뢰할 수 있는 정보 제공
2. 실무에 적용 가능한 구체적 조언
3. 관련 법규 및 정책 반영
4. 추가 학습 자료 제안

**사용자 질문**: {user_question}

위 정보를 바탕으로 전문적이고 도움이 되는 답변을 제공해주세요.
""",
            PromptType.DATA_COLLECTION: """
당신은 데이터 수집 및 분석 전문가입니다.

**역할**: 외부 API에서 수집된 데이터를 분석하고 정제하여 유용한 인사이트를 제공합니다.

**수집된 데이터**:
- 데이터 소스: {data_source}
- 수집 시간: {collection_time}
- 데이터 유형: {data_type}
- 원본 데이터: {raw_data}

**분석 요청**: {analysis_request}

**분석 결과 형식**:
1. 데이터 품질 평가
2. 핵심 정보 추출
3. 트렌드 및 패턴 분석
4. 정책적 시사점
5. 추가 수집 권장사항

위 데이터를 바탕으로 전문적인 분석을 수행해주세요.
""",
        }

    def _initialize_system_prompts(self) -> Dict[str, str]:
        """시스템 프롬프트 초기화"""
        return {
            "default": """
당신은 한국육아정책연구소(KICCE)의 디지털연수 특화 AI 어시스턴트입니다.

**전문 분야**:
- 육아정책 및 제도
- 아동발달 및 교육
- 부모교육 및 상담
- 디지털 육아 트렌드
- 관련 법규 및 정책

**응답 원칙**:
1. 정확하고 신뢰할 수 있는 정보 제공
2. 실무에 적용 가능한 구체적 조언
3. 관련 법규 및 정책 반영
4. 사용자 수준에 맞는 설명
5. 추가 학습 자료 제안

**응답 형식**:
- 명확하고 구조화된 답변
- 구체적인 예시와 사례
- 관련 법규나 정책 언급
- 추가 학습 자료 제안
""",
            "competency_expert": """
당신은 역량진단 및 평가 전문가입니다.

**전문 분야**:
- 역량 모델링 및 평가
- 개인별 맞춤형 학습 설계
- 성과 분석 및 피드백
- 학습 경로 최적화

**진단 원칙**:
1. 객관적이고 공정한 평가
2. 개인별 특성 고려
3. 구체적이고 실행 가능한 피드백
4. 성장 지향적 접근
""",
            "recommendation_expert": """
당신은 개인화된 학습 추천 전문가입니다.

**전문 분야**:
- 학습자 분석 및 프로파일링
- 맞춤형 학습 경로 설계
- 학습 자료 큐레이션
- 학습 효과성 평가

**추천 원칙**:
1. 개인별 특성과 선호도 반영
2. 학습 목표와 연계
3. 단계적 학습 경로 제시
4. 지속적 학습 동기 부여
""",
        }

    def get_prompt(self, prompt_type: PromptType, **kwargs) -> str:
        """
        프롬프트 템플릿 조회 및 변수 치환

        우선순위:
        1. 마크다운 파일 (src/agents/{agent_name}/prompts/)
        2. Fallback: 인라인 템플릿 (self.templates)
        """
        try:
            # 1. 마크다운 파일에서 로드 시도
            agent_name = self._type_to_agent.get(prompt_type)
            if agent_name:
                # prompt_type의 값을 파일명으로 사용 (예: "search", "assess", "analyze")
                prompt_file_name = self._get_prompt_file_name(prompt_type)
                try:
                    template = self.prompt_loader.load(
                        agent_name=agent_name, prompt_type=prompt_file_name, **kwargs
                    )
                    logger.debug(
                        f"Loaded prompt from markdown: {agent_name}/{prompt_file_name}"
                    )
                    return template
                except FileNotFoundError:
                    logger.debug(
                        f"Markdown file not found, using fallback: {agent_name}/{prompt_file_name}"
                    )

            # 2. Fallback: 인라인 템플릿 사용
            template = self.templates.get(prompt_type, "")
            if not template:
                logger.warning(f"Template not found for type: {prompt_type}")
                return ""

            # 변수 치환
            formatted_prompt = template.format(**kwargs)
            return formatted_prompt

        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template if "template" in locals() else ""
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            return template if "template" in locals() else ""

    def _get_prompt_file_name(self, prompt_type: PromptType) -> str:
        """
        PromptType에서 마크다운 파일명을 추출합니다.

        매핑:
        - COMPETENCY_ASSESSMENT -> "assess"
        - RECOMMENDATION -> "recommend"
        - SEARCH -> "search"
        - ANALYTICS -> "analyze"
        - GENERAL_CHAT -> "onboard"
        - DATA_COLLECTION -> "analyze"
        """
        mapping = {
            PromptType.COMPETENCY_ASSESSMENT: "assess",
            PromptType.RECOMMENDATION: "recommend",
            PromptType.SEARCH: "search",
            PromptType.ANALYTICS: "analyze",
            PromptType.GENERAL_CHAT: "onboard",
            PromptType.DATA_COLLECTION: "analyze",
        }
        return mapping.get(prompt_type, prompt_type.value)

    def get_system_prompt(
        self, role: str = "default", agent_name: Optional[str] = None
    ) -> str:
        """
        시스템 프롬프트 조회

        우선순위:
        1. 마크다운 파일 (src/agents/{agent_name}/prompts/system.md)
        2. Fallback: 인라인 시스템 프롬프트

        Args:
            role: 시스템 프롬프트 역할 (default, competency_expert, recommendation_expert)
            agent_name: 에이전트 이름 (제공 시 마크다운 파일 우선 로드)
        """
        # 1. 마크다운 파일에서 로드 시도
        if agent_name:
            try:
                system_prompt = self.prompt_loader.load(
                    agent_name=agent_name, prompt_type="system"
                )
                logger.debug(f"Loaded system prompt from markdown: {agent_name}/system")
                return system_prompt
            except FileNotFoundError:
                logger.debug(
                    f"System prompt markdown not found for {agent_name}, using fallback"
                )

        # 2. Fallback: 인라인 시스템 프롬프트
        return self.system_prompts.get(role, self.system_prompts["default"])

    # ===== 이름/버전 기반 단일 인터페이스 =====
    def format_by_name(
        self,
        name: str,
        variables: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> str:
        """이름 기반 프롬프트 접근. version은 호환 목적으로 유지(현재 미사용)."""
        variables = variables or {}
        # 간단 A/B 실험: PROMPT_AB_TEST_ENABLED가 true이면 rag_answer의 지시문 강화 변형 사용 확률 50%
        try:
            from config.settings import get_settings

            st = get_settings()
            ab_enabled = bool(getattr(st, "PROMPT_AB_TEST_ENABLED", False))
        except Exception:
            ab_enabled = False
        # 시스템 프롬프트: 'system_default' 또는 사전 정의 키 직접 사용 가능
        if name == "system_default":
            return self.system_prompts.get("default", "")
        if name in self.system_prompts:
            return self.system_prompts.get(name, "")

        # RAG 기본 응답 템플릿
        if name == "rag_answer":
            try:
                base = self._rag_answer_template
                if ab_enabled:
                    # A/B 변형: 출처 근거와 불확실성 명시 강조
                    import random

                    if random.random() < 0.5:
                        base = (
                            "You are a helpful assistant. Always cite sources from the context.\n"
                            "If uncertain, explicitly say you are uncertain.\n\n"
                            "Context:\n{context}\n\nQuestion: {question}"
                        )
                return base.format(**variables)
            except Exception:
                return self._rag_answer_template

        # 타입 매핑 템플릿
        if name in self._name_to_type:
            return self.get_prompt(self._name_to_type[name], **variables)

        logger.warning("Unknown prompt name: %s", name)
        return ""

    def create_rag_prompt(
        self,
        prompt_type: PromptType,
        user_input: str,
        retrieved_documents: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """RAG용 통합 프롬프트 생성"""
        try:
            # 검색된 문서 정보 포맷팅
            doc_context = self._format_retrieved_documents(retrieved_documents)

            # 컨텍스트 정보 준비
            context_info = context or {}
            context_info.update(
                {"retrieved_documents": doc_context, "user_input": user_input}
            )

            # 프롬프트 생성
            prompt = self.get_prompt(prompt_type, **context_info, **kwargs)

            return prompt

        except Exception as e:
            logger.error(f"Error creating RAG prompt: {e}")
            return user_input

    def _format_retrieved_documents(self, documents: List[Dict[str, Any]]) -> str:
        """검색된 문서들을 프롬프트용으로 포맷팅"""
        if not documents:
            return "관련 문서가 없습니다."

        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")
            score = doc.get("score", 0.0)
            metadata = doc.get("metadata", {})

            doc_info = f"""
문서 {i}:
- 내용: {content[:500]}{'...' if len(content) > 500 else ''}
- 관련도: {score:.2f}
- 출처: {metadata.get('source', 'Unknown')}
- 날짜: {metadata.get('date', 'Unknown')}
"""
            formatted_docs.append(doc_info)

        return "\n".join(formatted_docs)

    def get_conversation_prompt(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        retrieved_context: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """대화형 프롬프트 생성"""
        try:
            # 대화 히스토리 포맷팅
            history_text = ""
            for msg in conversation_history[-5:]:  # 최근 5개 메시지만
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

            # 사용자 프로필 정보
            profile_info = ""
            if user_profile:
                profile_info = f"""
사용자 프로필:
- 역량 수준: {user_profile.get('competency_level', 'Unknown')}
- 관심사: {', '.join(user_profile.get('interests', []))}
- 학습 선호도: {user_profile.get('learning_style', 'Unknown')}
"""

            # 검색된 컨텍스트 포맷팅
            context_text = self._format_retrieved_documents(retrieved_context)

            return f"""
{self.get_system_prompt()}

{profile_info}

이전 대화:
{history_text}

관련 정보:
{context_text}

현재 질문: {user_message}

위 정보를 바탕으로 전문적이고 도움이 되는 답변을 제공해주세요.
"""

        except Exception as e:
            logger.error(f"Error creating conversation prompt: {e}")
            return user_message
