from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.core.utils.agent_config import get_agent_runtime_config


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

    def _get_retrieval_engine(self):
        """RetrievalEngine 인스턴스 가져오기 (지연 로딩)"""
        if self._retrieval_engine is None:
            try:
                from src.rag.retrieval_engine import RetrievalEngine

                retrieval_config = dict(self.config.get("retrieval", {}))
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
        tags: List[str],
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

                similar.append(
                    {
                        "id": r.get("id", ""),
                        "handle": metadata.get("handle", ""),
                        "platform": metadata.get("platform", ""),
                        "score": round(r.get("score", 0), 4),
                        "followers": metadata.get("followers", 0),
                        "grade": metadata.get("grade", ""),
                        "tags": metadata.get("tags", []),
                    }
                )

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

    async def _analyze_risks_with_rag(
        self, handle: str, platform: str, risk_tags: List[str]
    ) -> str:
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
        provided_metrics: Dict[str, Any] = input_data.get("metrics", {}) or {}
        category: Optional[str] = input_data.get("category")

        # 1) fetch profile (via MCP HTTP)
        profile: Dict[str, Any] = {}
        if profile_url and profile_url.startswith("http"):
            try:
                from src.mcp import HttpMCP  # lazy import

                hmcp = HttpMCP()
                fetched = hmcp.fetch(profile_url)
                profile = {
                    "url": profile_url,
                    "fetched": True,
                    "content_type": fetched.get("content_type"),
                }
            except Exception as e:
                logger.info("HTTP fetch failed for %s: %s", profile_url, e)
                profile = {"url": profile_url, "fetched": False}
        profile.update(provided_metrics)

        # 2) derive signals (robust defaults)
        followers = _to_num(
            profile.get("followers") or profile.get("followers_count"), default=0
        )
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
        s_engage = _zclip(engagement_rate * 10, 0, 0.3)  # 10%→0.3
        s_freq = _zclip(frequency, 0, 0.15)  # 하루 1회→0.15
        s_fit = _zclip(brand_fit * 0.15, 0, 0.15)  # 도메인 적합도
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

                similar_creators, category_insights, risk_analysis, market_context = (
                    await asyncio.gather(
                        similar_task,
                        insights_task,
                        risk_task,
                        market_task,
                        return_exceptions=True,
                    )
                )

                # 예외 처리
                if isinstance(similar_creators, Exception):
                    logger.warning(
                        f"Similar creators search failed: {similar_creators}"
                    )
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
                    avg_score = sum(c.get("score", 0) for c in similar_creators) / len(
                        similar_creators
                    )
                    recommendation_context = f"유사 크리에이터 {len(similar_creators)}명 발견 (평균 유사도: {avg_score:.2f})"

                    # 유사 크리에이터의 성공 사례 참고
                    successful = [
                        c for c in similar_creators if c.get("grade") in ("S", "A")
                    ]
                    if successful:
                        recommendation_context += (
                            f" | 성공 사례 {len(successful)}건 참고 가능"
                        )

                rag_enhanced = RAGEnhancedData(
                    similar_creators=(
                        similar_creators if isinstance(similar_creators, list) else []
                    ),
                    category_insights=(
                        str(category_insights) if category_insights else ""
                    ),
                    risk_analysis=str(risk_analysis) if risk_analysis else "",
                    market_context=str(market_context) if market_context else "",
                    recommendation_context=recommendation_context,
                )

                # RAG 인사이트를 기반으로 추가 태그 생성
                if similar_creators and len(similar_creators) >= 3:
                    tags.append("has_similar_creators")
                if category_insights:
                    tags.append("category_insights_available")

            except Exception as e:
                logger.warning(f"RAG enhancement failed: {e}")
                rag_enhanced = None

        # 5) comprehensive report
        report_parts = [
            f"=== Creator Evaluation Report ===",
            f"Platform: {platform} | Handle: {handle}",
            f"Category: {category or 'Not specified'}",
            "",
            f"=== Metrics ===",
            f"Followers: {followers:,} | Engagement: {engagement_rate:.2%} | Posts(30d): {posts_30d}",
            f"Brand-fit: {brand_fit:.2f} | Reports(90d): {reports_90d}",
            "",
            f"=== Evaluation ===",
            f"Score: {score} / 100 | Grade: {grade} | Decision: {decision}",
            f"Risks: {', '.join(risk_tags) if risk_tags else 'None'}",
            f"Tags: {', '.join(tags) if tags else 'None'}",
        ]

        # RAG 향상 정보 추가
        if rag_enhanced:
            report_parts.append("")
            report_parts.append("=== RAG-Enhanced Insights ===")

            if rag_enhanced.similar_creators:
                report_parts.append(
                    f"Similar Creators Found: {len(rag_enhanced.similar_creators)}"
                )
                for i, sc in enumerate(rag_enhanced.similar_creators[:3], 1):
                    report_parts.append(
                        f"  {i}. @{sc.get('handle', 'unknown')} ({sc.get('platform', '')}) - "
                        f"Similarity: {sc.get('score', 0):.2f}, Grade: {sc.get('grade', 'N/A')}"
                    )

            if rag_enhanced.category_insights:
                report_parts.append(
                    f"Category Insights: {rag_enhanced.category_insights[:200]}"
                )

            if rag_enhanced.market_context:
                report_parts.append(
                    f"Market Context: {rag_enhanced.market_context[:200]}"
                )

            if rag_enhanced.risk_analysis and risk_tags:
                report_parts.append(
                    f"Risk Analysis: {rag_enhanced.risk_analysis[:200]}"
                )

            if rag_enhanced.recommendation_context:
                report_parts.append(
                    f"Recommendation: {rag_enhanced.recommendation_context}"
                )

        report = "\n".join(report_parts)

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
