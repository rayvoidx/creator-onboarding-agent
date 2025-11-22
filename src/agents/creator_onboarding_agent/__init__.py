from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from pathlib import Path

from src.utils.agent_config import get_agent_runtime_config
from src.core.utils.prompt_loader import PromptLoader
from config.settings import get_settings


logger = logging.getLogger(__name__)


@dataclass
class RAGEnhancedData:
    """RAG를 통해 수집된 향상된 데이터"""
    similar_creators: List[Dict[str, Any]] = field(default_factory=list)
    category_insights: str = ""
    risk_analysis: str = ""
    market_context: str = ""
    recommendation_context: str = ""


@dataclass
class CreatorEvaluationResult:
    success: bool
    platform: str
    handle: str
    decision: str
    grade: str
    score: float
    score_breakdown: Dict[str, float]
    tags: List[str]
    risks: List[str]
    report: str
    raw_profile: Dict[str, Any]
    rag_enhanced: Optional[RAGEnhancedData] = None


class CreatorOnboardingAgent:
    """Evaluate creators (TikTok/Instagram/etc.) for onboarding suitability.

    Steps (enhanced with RAG):
      1) Fetch public profile/metrics (via HTTP MCP)
      2) Derive basic signals (followers, engagement, post frequency)
      3) RAG-enhanced analysis (similar creators, market context, risks)
      4) Heuristic scoring + rule-based risks + RAG insights
      5) Grade + decision with comprehensive report
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        merged_config = get_agent_runtime_config("creator", config)
        self.config = merged_config
        self.agent_model_config = {
            "llm_models": merged_config.get("llm_models", []),
            "embedding_model": merged_config.get("embedding_model"),
            "vector_db": merged_config.get("vector_db"),
        }
        self._retrieval_engine = None
        self._use_rag = self.config.get("use_rag", True)
        self._llm = None
        # PromptLoader with correct path to src/agents
        agents_path = Path(__file__).parent.parent  # src/agents
        self._prompt_loader = PromptLoader(base_path=agents_path)

    def _get_llm(self):
        """LLM 인스턴스 가져오기 (지연 로딩)"""
        if self._llm is None:
            try:
                from langchain_anthropic import ChatAnthropic
                from langchain_openai import ChatOpenAI

                settings = get_settings()
                llm_models = self.agent_model_config.get("llm_models", [])

                # 선호 모델 순서대로 시도
                for model_name in llm_models:
                    try:
                        if "claude" in model_name.lower() and settings.ANTHROPIC_API_KEY:
                            self._llm = ChatAnthropic(
                                model=model_name,
                                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                                temperature=0.3,
                                max_tokens=2000
                            )
                            logger.info(f"CreatorOnboardingAgent: Using {model_name}")
                            break
                        elif "gpt" in model_name.lower() and settings.OPENAI_API_KEY:
                            self._llm = ChatOpenAI(
                                model=model_name,
                                openai_api_key=settings.OPENAI_API_KEY,
                                temperature=0.3,
                                max_tokens=2000
                            )
                            logger.info(f"CreatorOnboardingAgent: Using {model_name}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to init {model_name}: {e}")
                        continue

                # 폴백: 기본 모델
                if self._llm is None:
                    if settings.ANTHROPIC_API_KEY:
                        self._llm = ChatAnthropic(
                            model=settings.ANTHROPIC_MODEL_NAME,
                            anthropic_api_key=settings.ANTHROPIC_API_KEY,
                            temperature=0.3,
                            max_tokens=2000
                        )
                        logger.info(f"CreatorOnboardingAgent: Fallback to {settings.ANTHROPIC_MODEL_NAME}")
                    elif settings.OPENAI_API_KEY:
                        self._llm = ChatOpenAI(
                            model=settings.OPENAI_MODEL_NAME,
                            openai_api_key=settings.OPENAI_API_KEY,
                            temperature=0.3,
                            max_tokens=2000
                        )
                        logger.info(f"CreatorOnboardingAgent: Fallback to {settings.OPENAI_MODEL_NAME}")

            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                self._llm = None
        return self._llm

    async def _generate_llm_report(
        self,
        platform: str,
        handle: str,
        followers: int,
        avg_likes: int,
        avg_comments: int,
        posts_30d: int,
        reports_90d: int,
        brand_fit: float,
        engagement_rate: float,
        frequency: float,
        score: float,
        grade: str,
        decision: str,
        score_breakdown: Dict[str, float],
        risks: List[str],
        tags: List[str],
        rag_enhanced: Optional[RAGEnhancedData] = None
    ) -> str:
        """LLM을 사용하여 상세 평가 리포트 생성"""
        llm = self._get_llm()
        if not llm:
            return self._generate_basic_report(
                platform, handle, followers, engagement_rate, posts_30d,
                reports_90d, brand_fit, score, grade, decision, risks, tags
            )

        try:
            # 시스템 프롬프트 로드
            system_prompt = self._prompt_loader.load(
                "creator_onboarding_agent", "system"
            )

            # 사용자 프롬프트 구성
            user_prompt = f"""다음 크리에이터의 온보딩 평가를 분석하고 상세 리포트를 작성해주세요.

## 크리에이터 정보
- 플랫폼: {platform}
- 핸들: @{handle}

## 메트릭
- 팔로워: {followers:,}명
- 평균 좋아요: {avg_likes:,}
- 평균 댓글: {avg_comments:,}
- 30일 게시물: {posts_30d}개
- 90일 신고: {reports_90d}회
- 브랜드 적합도: {brand_fit:.2f}
- 참여율: {engagement_rate:.2%}
- 일평균 게시물: {frequency:.2f}

## 평가 결과
- 최종 점수: {score}/100
- 등급: {grade}
- 결정: {decision}

## 점수 구성
- 팔로워 영향력: {score_breakdown.get('followers', 0):.1f}/40
- 참여율: {score_breakdown.get('engagement', 0):.1f}/30
- 활동 빈도: {score_breakdown.get('frequency', 0):.1f}/15
- 브랜드 적합도: {score_breakdown.get('brand_fit', 0):.1f}/15

## 리스크
{', '.join(risks) if risks else '없음'}

## 태그
{', '.join(tags) if tags else '없음'}
"""

            # RAG 인사이트 추가
            if rag_enhanced:
                if rag_enhanced.similar_creators:
                    user_prompt += f"\n## 유사 크리에이터\n{len(rag_enhanced.similar_creators)}명 발견\n"
                if rag_enhanced.category_insights:
                    user_prompt += f"\n## 카테고리 인사이트\n{rag_enhanced.category_insights[:300]}\n"
                if rag_enhanced.market_context:
                    user_prompt += f"\n## 시장 컨텍스트\n{rag_enhanced.market_context[:300]}\n"

            user_prompt += """
위 데이터를 바탕으로 다음 형식의 리포트를 작성해주세요:

## 크리에이터 평가 리포트

### 핵심 요약
[이 크리에이터의 가장 큰 강점과 약점, 최종 결정의 근거를 2-3문장으로 요약]

### 강점 분석
[점수가 높은 영역과 브랜드 파트너십에서 기대할 수 있는 가치]

### 개선 영역
[점수가 낮거나 리스크가 있는 영역과 구체적인 개선 방안]

### 권장 사항
[어떤 캠페인에 적합한지, 또는 재평가를 위한 조건]

### 다음 단계
[구체적인 액션 아이템 2-3개]
"""

            from langchain_core.messages import SystemMessage, HumanMessage

            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])

            return response.content

        except Exception as e:
            logger.warning(f"LLM report generation failed: {e}")
            return self._generate_basic_report(
                platform, handle, followers, engagement_rate, posts_30d,
                reports_90d, brand_fit, score, grade, decision, risks, tags
            )

    def _generate_basic_report(
        self,
        platform: str,
        handle: str,
        followers: int,
        engagement_rate: float,
        posts_30d: int,
        reports_90d: int,
        brand_fit: float,
        score: float,
        grade: str,
        decision: str,
        risks: List[str],
        tags: List[str]
    ) -> str:
        """기본 리포트 생성 (LLM 실패 시 폴백)"""
        return f"""=== Creator Evaluation Report ===
Platform: {platform} | Handle: {handle}

=== Metrics ===
Followers: {followers:,} | Engagement: {engagement_rate:.2%} | Posts(30d): {posts_30d}
Brand-fit: {brand_fit:.2f} | Reports(90d): {reports_90d}

=== Evaluation ===
Score: {score} / 100 | Grade: {grade} | Decision: {decision}
Risks: {', '.join(risks) if risks else 'None'}
Tags: {', '.join(tags) if tags else 'None'}"""

    def _get_retrieval_engine(self):
        """RetrievalEngine 인스턴스 가져오기 (지연 로딩)"""
        if self._retrieval_engine is None:
            try:
                from src.rag.retrieval_engine import RetrievalEngine

                retrieval_config = dict(self.config.get('retrieval', {}))
                embedding_model = self.agent_model_config.get("embedding_model")
                vector_db = self.agent_model_config.get("vector_db")
                if embedding_model:
                    retrieval_config.setdefault("embedding_model", embedding_model)
                if vector_db:
                    retrieval_config.setdefault("vector_db", vector_db)
                self._retrieval_engine = RetrievalEngine(retrieval_config)
            except Exception as e:
                logger.warning(f"Failed to initialize RetrievalEngine: {e}")
                self._retrieval_engine = None
        return self._retrieval_engine

    async def _find_similar_creators(
        self,
        platform: str,
        handle: str,
        category: Optional[str],
        followers: int,
        tags: List[str]
    ) -> List[Dict[str, Any]]:
        """유사 크리에이터 검색"""
        engine = self._get_retrieval_engine()
        if not engine:
            return []

        try:
            # 검색 쿼리 구성
            query_parts = [f"platform:{platform}"]

            if category:
                query_parts.append(category)

            if tags:
                query_parts.extend(tags[:3])

            # 팔로워 규모에 따른 분류
            if followers >= 1_000_000:
                query_parts.append("mega influencer")
            elif followers >= 100_000:
                query_parts.append("macro influencer")
            elif followers >= 10_000:
                query_parts.append("micro influencer")
            else:
                query_parts.append("nano influencer")

            query = " ".join(query_parts)

            # 하이브리드 검색 실행
            results = await engine.hybrid_search(query, limit=10)

            # 자기 자신 제외하고 상위 5개 반환
            similar = []
            for r in results:
                metadata = r.get("metadata", {})
                result_handle = metadata.get("handle", "").lower()

                if result_handle and result_handle == handle.lower():
                    continue

                similar.append({
                    "id": r.get("id", ""),
                    "handle": metadata.get("handle", ""),
                    "platform": metadata.get("platform", ""),
                    "score": round(r.get("score", 0), 4),
                    "followers": metadata.get("followers", 0),
                    "grade": metadata.get("grade", ""),
                    "tags": metadata.get("tags", [])
                })

                if len(similar) >= 5:
                    break

            return similar

        except Exception as e:
            logger.warning(f"Similar creators search failed: {e}")
            return []

    async def _get_category_insights(self, category: str, platform: str) -> str:
        """카테고리 인사이트 검색"""
        engine = self._get_retrieval_engine()
        if not engine or not category:
            return ""

        try:
            query = f"{category} {platform} 크리에이터 트렌드 인사이트"
            results = await engine.vector_search(query, limit=3)

            if not results:
                return ""

            insights = []
            for r in results:
                content = r.get("content", "")[:200]
                if content:
                    insights.append(content)

            return " | ".join(insights) if insights else ""

        except Exception as e:
            logger.warning(f"Category insights search failed: {e}")
            return ""

    async def _analyze_risks_with_rag(self, handle: str, platform: str, risk_tags: List[str]) -> str:
        """RAG 기반 리스크 분석"""
        engine = self._get_retrieval_engine()
        if not engine or not risk_tags:
            return ""

        try:
            # 리스크 관련 정보 검색
            risk_query = f"{platform} {' '.join(risk_tags)} 리스크 분석 대응 전략"
            results = await engine.vector_search(risk_query, limit=3)

            if not results:
                return ""

            analysis_parts = []
            for r in results:
                content = r.get("content", "")[:150]
                if content:
                    analysis_parts.append(content)

            return " | ".join(analysis_parts) if analysis_parts else ""

        except Exception as e:
            logger.warning(f"Risk analysis search failed: {e}")
            return ""

    async def _get_market_context(self, platform: str, followers: int) -> str:
        """시장 컨텍스트 검색"""
        engine = self._get_retrieval_engine()
        if not engine:
            return ""

        try:
            # 팔로워 규모에 따른 시장 분류
            if followers >= 1_000_000:
                tier = "메가 인플루언서"
            elif followers >= 100_000:
                tier = "매크로 인플루언서"
            elif followers >= 10_000:
                tier = "마이크로 인플루언서"
            else:
                tier = "나노 인플루언서"

            query = f"{platform} {tier} 시장 동향 협업 가격"
            results = await engine.vector_search(query, limit=2)

            if not results:
                return ""

            context_parts = []
            for r in results:
                content = r.get("content", "")[:150]
                if content:
                    context_parts.append(content)

            return " | ".join(context_parts) if context_parts else ""

        except Exception as e:
            logger.warning(f"Market context search failed: {e}")
            return ""

    async def execute(self, input_data: Dict[str, Any]) -> CreatorEvaluationResult:
        platform: str = str(input_data.get("platform", "")).lower()
        handle: str = str(input_data.get("handle", "")).strip()
        profile_url: Optional[str] = input_data.get("profile_url")
        category: Optional[str] = input_data.get("category")

        # metrics는 nested dict 또는 최상위 레벨에서 직접 제공될 수 있음
        provided_metrics: Dict[str, Any] = input_data.get("metrics", {}) or {}

        # 최상위 레벨에 직접 제공된 값들을 metrics에 병합
        direct_fields = ["followers", "avg_likes", "avg_comments", "posts_30d",
                        "reports_90d", "brand_fit", "tags", "followers_count"]
        for field in direct_fields:
            if field in input_data and field not in provided_metrics:
                provided_metrics[field] = input_data[field]

        # 1) fetch profile (via Supadata MCP)
        profile: Dict[str, Any] = {}
        if profile_url and profile_url.startswith("http"):
            try:
                from src.services.supadata_mcp import SupadataMCPClient  # lazy import
                supadata_client = SupadataMCPClient()

                if supadata_client.available:
                    # Supadata MCP를 통해 SNS 프로필 스크래핑
                    scraped_results = await supadata_client.scrape_urls([profile_url])

                    if scraped_results:
                        scraped_data = scraped_results[0]
                        profile = {
                            "url": profile_url,
                            "fetched": True,
                            "scraped_content": scraped_data,
                        }

                        # 스크래핑된 데이터에서 메트릭 추출 시도
                        content = scraped_data.get("content", [])
                        all_text = ""
                        if content and isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict):
                                    text = block.get("text", "")
                                    all_text += text + "\n"

                        # raw_text 저장
                        profile["raw_text"] = all_text

                        # 자동 메트릭 추출
                        if all_text:
                            extracted_metrics = _extract_metrics_from_text(all_text, platform)
                            if extracted_metrics:
                                # 추출된 메트릭을 프로필에 병합 (기존 값이 없는 경우만)
                                for key, value in extracted_metrics.items():
                                    if key not in profile or not profile.get(key):
                                        profile[key] = value
                                logger.info("Auto-extracted metrics: %s", list(extracted_metrics.keys()))

                        logger.info("Successfully scraped profile via Supadata MCP: %s", profile_url)
                    else:
                        profile = {"url": profile_url, "fetched": False, "error": "No results from Supadata"}
                        logger.warning("Supadata MCP returned no results for: %s", profile_url)
                else:
                    # Supadata가 사용 불가능한 경우 기본 프로필 설정
                    profile = {"url": profile_url, "fetched": False, "error": "Supadata MCP not available"}
                    logger.warning("Supadata MCP not available, skipping scrape for: %s", profile_url)

            except Exception as e:
                logger.warning("Supadata MCP scrape failed for %s: %s", profile_url, e)
                profile = {"url": profile_url, "fetched": False, "error": str(e)}
        profile.update(provided_metrics)

        # 2) derive signals (robust defaults)
        followers = _to_num(profile.get("followers") or profile.get("followers_count"), default=0)
        avg_likes = _to_num(profile.get("avg_likes"), default=0)
        avg_comments = _to_num(profile.get("avg_comments"), default=0)
        posts_30d = _to_num(profile.get("posts_30d"), default=0)
        reports_90d = _to_num(profile.get("reports_90d"), default=0)
        brand_fit = float(profile.get("brand_fit", 0.0))  # 0~1 수치 (옵션)
        profile_tags: List[str] = profile.get("tags", []) or []

        engagement_rate = _safe_div(avg_likes + 2 * avg_comments, max(1, followers))
        frequency = posts_30d / 30.0

        # 3) scoring (simple heuristic)
        s_followers = _zclip(followers / 1_000_000, 0, 0.4)  # 100만 팔로워→0.4
        s_engage = _zclip(engagement_rate * 10, 0, 0.3)      # 10%→0.3
        s_freq = _zclip(frequency, 0, 0.15)                  # 하루 1회→0.15
        s_fit = _zclip(brand_fit * 0.15, 0, 0.15)            # 도메인 적합도
        base_score = s_followers + s_engage + s_freq + s_fit

        # risk penalties
        risk_tags: List[str] = []
        if reports_90d >= 3:
            base_score -= 0.15
            risk_tags.append("high_reports")
        if engagement_rate < 0.002:
            base_score -= 0.1
            risk_tags.append("low_engagement")
        if posts_30d < 4:
            base_score -= 0.05
            risk_tags.append("low_activity")

        score = float(round(max(0.0, min(1.0, base_score)) * 100, 1))
        grade, decision, tags = _grade_and_decide(score, risk_tags)

        # 4) RAG-enhanced analysis (if enabled)
        rag_enhanced: Optional[RAGEnhancedData] = None

        if self._use_rag:
            try:
                import asyncio

                # 병렬로 RAG 분석 수행
                similar_task = self._find_similar_creators(
                    platform, handle, category, followers, profile_tags
                )
                insights_task = self._get_category_insights(category or "", platform)
                risk_task = self._analyze_risks_with_rag(handle, platform, risk_tags)
                market_task = self._get_market_context(platform, followers)

                similar_creators, category_insights, risk_analysis, market_context = await asyncio.gather(
                    similar_task, insights_task, risk_task, market_task,
                    return_exceptions=True
                )

                # 예외 처리
                if isinstance(similar_creators, Exception):
                    logger.warning(f"Similar creators search failed: {similar_creators}")
                    similar_creators = []
                if isinstance(category_insights, Exception):
                    category_insights = ""
                if isinstance(risk_analysis, Exception):
                    risk_analysis = ""
                if isinstance(market_context, Exception):
                    market_context = ""

                # 유사 크리에이터 기반 추천 컨텍스트 생성
                recommendation_context = ""
                if similar_creators:
                    avg_score = sum(c.get("score", 0) for c in similar_creators) / len(similar_creators)
                    recommendation_context = f"유사 크리에이터 {len(similar_creators)}명 발견 (평균 유사도: {avg_score:.2f})"

                    # 유사 크리에이터의 성공 사례 참고
                    successful = [c for c in similar_creators if c.get("grade") in ("S", "A")]
                    if successful:
                        recommendation_context += f" | 성공 사례 {len(successful)}건 참고 가능"

                rag_enhanced = RAGEnhancedData(
                    similar_creators=similar_creators if isinstance(similar_creators, list) else [],
                    category_insights=str(category_insights) if category_insights else "",
                    risk_analysis=str(risk_analysis) if risk_analysis else "",
                    market_context=str(market_context) if market_context else "",
                    recommendation_context=recommendation_context
                )

                # RAG 인사이트를 기반으로 추가 태그 생성
                if similar_creators and len(similar_creators) >= 3:
                    tags.append("has_similar_creators")
                if category_insights:
                    tags.append("category_insights_available")

            except Exception as e:
                logger.warning(f"RAG enhancement failed: {e}")
                rag_enhanced = None

        # 5) LLM-enhanced comprehensive report
        score_breakdown = {
            "followers": round(s_followers * 100, 1),
            "engagement": round(s_engage * 100, 1),
            "frequency": round(s_freq * 100, 1),
            "brand_fit": round(s_fit * 100, 1),
        }

        report = await self._generate_llm_report(
            platform=platform,
            handle=handle,
            followers=followers,
            avg_likes=avg_likes,
            avg_comments=avg_comments,
            posts_30d=posts_30d,
            reports_90d=reports_90d,
            brand_fit=brand_fit,
            engagement_rate=engagement_rate,
            frequency=frequency,
            score=score,
            grade=grade,
            decision=decision,
            score_breakdown=score_breakdown,
            risks=risk_tags,
            tags=tags,
            rag_enhanced=rag_enhanced
        )

        return CreatorEvaluationResult(
            success=True,
            platform=platform,
            handle=handle,
            decision=decision,
            grade=grade,
            score=score,
            score_breakdown={
                "followers": round(s_followers * 100, 1),
                "engagement": round(s_engage * 100, 1),
                "frequency": round(s_freq * 100, 1),
                "brand_fit": round(s_fit * 100, 1),
            },
            tags=tags,
            risks=risk_tags,
            report=report,
            raw_profile=profile,
            rag_enhanced=rag_enhanced,
        )


def _to_num(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).replace(",", "").strip()
        return int(float(s))
    except Exception:
        return default


def _safe_div(a: float, b: float) -> float:
    try:
        return float(a) / float(b) if b else 0.0
    except Exception:
        return 0.0


def _zclip(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _grade_and_decide(score: float, risk_tags: List[str]) -> tuple[str, str, List[str]]:
    grade = "C"
    if score >= 85:
        grade = "S"
    elif score >= 70:
        grade = "A"
    elif score >= 55:
        grade = "B"

    decision = "accept"
    if "high_reports" in risk_tags or score < 50:
        decision = "reject"
    elif "low_activity" in risk_tags and score < 70:
        decision = "hold"

    tags: List[str] = []
    if grade in ("S", "A"):
        tags.append("top_candidate")
    if "low_engagement" in risk_tags:
        tags.append("needs_awareness_campaign")
    if "low_activity" in risk_tags:
        tags.append("needs_activation")

    return grade, decision, tags


def _extract_metrics_from_text(text: str, platform: str = "") -> Dict[str, Any]:
    """스크래핑된 텍스트에서 SNS 메트릭을 자동 추출

    Instagram, TikTok 등 SNS 프로필 텍스트에서 팔로워, 게시물 수 등을 파싱합니다.
    """
    metrics: Dict[str, Any] = {}

    if not text:
        return metrics

    # 텍스트 정규화
    text_lower = text.lower()

    def parse_count(s: str) -> int:
        """숫자 문자열을 정수로 변환 (K, M 단위 지원)"""
        s = s.strip().replace(",", "").replace(" ", "")
        multiplier = 1

        if s.endswith("k") or s.endswith("천"):
            s = s[:-1]
            multiplier = 1_000
        elif s.endswith("m") or s.endswith("백만"):
            s = s[:-1]
            multiplier = 1_000_000
        elif s.endswith("만"):
            s = s[:-1]
            multiplier = 10_000

        try:
            return int(float(s) * multiplier)
        except (ValueError, TypeError):
            return 0

    # 팔로워 수 추출 패턴들
    follower_patterns = [
        # Instagram 형식: "1,234 followers", "1.2M followers"
        r"([\d,.]+[kKmM]?)\s*(?:followers?|팔로워)",
        # TikTok 형식: "1234 Followers"
        r"([\d,.]+[kKmM]?)\s*Followers?",
        # 한국어: "팔로워 1,234" 또는 "팔로워: 1,234"
        r"팔로워[:\s]*([\d,.]+[kKmM만천]?)",
        # 숫자 followers 형식
        r"([\d,.]+)\s*(?:명|명의)?\s*팔로워",
        # Instagram JSON/메타데이터 형식
        r'"edge_followed_by"[^}]*"count":\s*(\d+)',
        r'"follower_count":\s*(\d+)',
    ]

    for pattern in follower_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = parse_count(match.group(1))
            if count > 0:
                metrics["followers"] = count
                logger.info(f"Extracted followers: {count}")
                break

    # 팔로잉 수 추출
    following_patterns = [
        r"([\d,.]+[kKmM]?)\s*(?:following|팔로잉)",
        r"팔로잉[:\s]*([\d,.]+[kKmM만천]?)",
        r'"edge_follow"[^}]*"count":\s*(\d+)',
    ]

    for pattern in following_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = parse_count(match.group(1))
            if count > 0:
                metrics["following"] = count
                break

    # 게시물 수 추출
    posts_patterns = [
        r"([\d,.]+)\s*(?:posts?|게시물)",
        r"게시물[:\s]*([\d,.]+)",
        r'"edge_owner_to_timeline_media"[^}]*"count":\s*(\d+)',
        r'"media_count":\s*(\d+)',
    ]

    for pattern in posts_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            count = parse_count(match.group(1))
            if count > 0:
                metrics["total_posts"] = count
                # posts_30d 추정: 전체 게시물의 약 10% 또는 최소 4개
                estimated_monthly = max(4, count // 10)
                metrics["posts_30d"] = min(estimated_monthly, 30)  # 최대 30개/월
                logger.info(f"Extracted posts: {count}, estimated posts_30d: {metrics['posts_30d']}")
                break

    # 좋아요 수 추출 (평균 추정)
    likes_patterns = [
        r"([\d,.]+[kKmM]?)\s*(?:likes?|좋아요)",
        r'"edge_liked_by"[^}]*"count":\s*(\d+)',
        r'"like_count":\s*(\d+)',
    ]

    total_likes = 0
    like_count = 0
    for pattern in likes_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            count = parse_count(match)
            if count > 0:
                total_likes += count
                like_count += 1

    if like_count > 0:
        metrics["avg_likes"] = total_likes // like_count
        logger.info(f"Extracted avg_likes: {metrics['avg_likes']}")
    elif "followers" in metrics:
        # 팔로워 기반 평균 좋아요 추정 (약 3% 참여율 가정)
        metrics["avg_likes"] = max(10, metrics["followers"] // 30)

    # 댓글 수 추출 (평균 추정)
    comments_patterns = [
        r"([\d,.]+[kKmM]?)\s*(?:comments?|댓글)",
        r'"edge_media_to_comment"[^}]*"count":\s*(\d+)',
        r'"comment_count":\s*(\d+)',
    ]

    total_comments = 0
    comment_count = 0
    for pattern in comments_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            count = parse_count(match)
            if count > 0:
                total_comments += count
                comment_count += 1

    if comment_count > 0:
        metrics["avg_comments"] = total_comments // comment_count
        logger.info(f"Extracted avg_comments: {metrics['avg_comments']}")
    elif "avg_likes" in metrics:
        # 좋아요 기반 댓글 추정 (좋아요의 약 2-5%)
        metrics["avg_comments"] = max(1, metrics["avg_likes"] // 30)

    # 비디오 조회수 (TikTok용)
    views_patterns = [
        r"([\d,.]+[kKmM]?)\s*(?:views?|조회수)",
        r'"play_count":\s*(\d+)',
    ]

    total_views = 0
    view_count = 0
    for pattern in views_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            count = parse_count(match)
            if count > 0:
                total_views += count
                view_count += 1

    if view_count > 0:
        metrics["avg_views"] = total_views // view_count

    # 플랫폼별 추가 처리
    if platform.lower() == "instagram":
        # Instagram 프로필에서 bio/description 추출
        bio_patterns = [
            r'"biography":\s*"([^"]*)"',
            r'"bio":\s*"([^"]*)"',
        ]
        for pattern in bio_patterns:
            match = re.search(pattern, text)
            if match:
                metrics["bio"] = match.group(1)[:200]
                break

    elif platform.lower() == "tiktok":
        # TikTok 특화 메트릭
        if "avg_views" in metrics and "followers" in metrics:
            # TikTok은 조회수 기반 참여율이 더 중요
            if not metrics.get("avg_likes"):
                metrics["avg_likes"] = max(10, metrics["avg_views"] // 20)

    # 추출된 메트릭 요약 로그
    if metrics:
        logger.info(f"Extracted metrics from text: {list(metrics.keys())}")
    else:
        logger.warning("No metrics could be extracted from text")

    return metrics


