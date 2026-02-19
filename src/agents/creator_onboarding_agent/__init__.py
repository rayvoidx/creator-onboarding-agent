from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config.settings import Settings
from src.core.utils.agent_config import get_agent_runtime_config

logger = logging.getLogger(__name__)

# Platform → profile URL templates
_PLATFORM_URL_TEMPLATES: Dict[str, str] = {
    "instagram": "https://www.instagram.com/{handle}/",
    "tiktok": "https://www.tiktok.com/@{handle}",
    "youtube": "https://www.youtube.com/@{handle}",
    "twitter": "https://twitter.com/{handle}",
    "x": "https://x.com/{handle}",
}


def _build_profile_url(platform: str, handle: str) -> str:
    """Build a public profile URL from platform + handle."""
    clean = handle.lstrip("@").strip()
    tpl = _PLATFORM_URL_TEMPLATES.get(platform, "")
    if not tpl or not clean:
        return ""
    return tpl.format(handle=clean)


def _parse_number_from_text(text: str) -> int:
    """Parse numbers like '1.2M', '543K', '12,345' from scraped text."""
    if not text:
        return 0
    text = text.strip().upper().replace(",", "").replace(" ", "")
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return int(float(text[:-1]) * mult)
            except (ValueError, TypeError):
                return 0
    try:
        return int(float(re.sub(r"[^\d.]", "", text)))
    except (ValueError, TypeError):
        return 0


def _extract_metrics_from_scraped(content: str, platform: str) -> Dict[str, Any]:
    """Extract follower/engagement metrics from scraped HTML/text content.

    Data confidence levels:
      - "verified": from og:description or structured JSON (100% accurate)
      - "estimated": inferred from verified data (approximate)
      - "unavailable": requires login, cannot be scraped
    """
    metrics: Dict[str, Any] = {}
    data_sources: Dict[str, str] = {}  # field → "verified" | "estimated"
    if not content:
        return metrics

    text = content.lower()

    # ── Priority 1: og:description (most reliable for Instagram) ──
    # Format: "90K Followers, 3,368 Following, 558 Posts - ..."
    og_match = re.search(
        r"([\d,.]+[kmb]?)\s*followers?,\s*([\d,.]+[kmb]?)\s*following,\s*([\d,.]+[kmb]?)\s*posts?",
        text,
    )
    if og_match:
        f_val = _parse_number_from_text(og_match.group(1))
        fg_val = _parse_number_from_text(og_match.group(2))
        p_val = _parse_number_from_text(og_match.group(3))
        if f_val > 0:
            metrics["followers"] = f_val
            data_sources["followers"] = "verified"
        if fg_val > 0:
            metrics["following"] = fg_val
            data_sources["following"] = "verified"
        if p_val > 0:
            metrics["total_posts"] = p_val
            data_sources["total_posts"] = "verified"

    # ── Priority 2: Structured JSON patterns (fallback) ──
    if "followers" not in metrics:
        json_follower_patterns = [
            r'"edge_followed_by"[:\s]*\{["\s]*count["\s]*[:\s]*([\d]+)',
            r'"followercount"[:\s]*([\d]+)',
            r'"subscribercount"[:\s]*"?([\d]+)"?',
        ]
        for pat in json_follower_patterns:
            m = re.search(pat, text)
            if m:
                val = _parse_number_from_text(m.group(1))
                if val > 0:
                    metrics["followers"] = val
                    data_sources["followers"] = "verified"
                    break

    if "following" not in metrics:
        m = re.search(r'"edge_follow"[:\s]*\{["\s]*count["\s]*[:\s]*([\d]+)', text)
        if m:
            metrics["following"] = _parse_number_from_text(m.group(1))
            data_sources["following"] = "verified"

    if "total_posts" not in metrics:
        json_post_patterns = [
            r'"edge_owner_to_timeline_media"[:\s]*\{["\s]*count["\s]*[:\s]*([\d]+)',
            r'"videocount"[:\s]*([\d]+)',
        ]
        for pat in json_post_patterns:
            m = re.search(pat, text)
            if m:
                val = _parse_number_from_text(m.group(1))
                if val > 0:
                    metrics["total_posts"] = val
                    data_sources["total_posts"] = "verified"
                    break

    # ── Priority 3: Generic regex (least reliable) ──
    if "followers" not in metrics:
        for pat in [
            r"([\d,.]+[kmb]?)\s*(?:followers|팔로워|subscribers|구독자)",
            r"(?:followers|팔로워)[:\s]*([\d,.]+[kmb]?)",
        ]:
            m = re.search(pat, text)
            if m:
                val = _parse_number_from_text(m.group(1))
                if val > 0:
                    metrics["followers"] = val
                    data_sources["followers"] = "verified"
                    break

    if "total_posts" not in metrics:
        m = re.search(r"([\d,.]+[kmb]?)\s*(?:posts|게시물|게시글)", text)
        if m:
            val = _parse_number_from_text(m.group(1))
            if val > 0:
                metrics["total_posts"] = val
                data_sources["total_posts"] = "verified"

    if "following" not in metrics:
        m = re.search(r"([\d,.]+[kmb]?)\s*(?:following|팔로잉)", text)
        if m:
            val = _parse_number_from_text(m.group(1))
            if val > 0:
                metrics["following"] = val
                data_sources["following"] = "verified"

    # ── Direct likes data (if available in page) ──
    like_counts = re.findall(r'"edge_media_preview_like":\{"count":(\d+)\}', text)
    if like_counts:
        likes = [int(x) for x in like_counts]
        metrics["avg_likes"] = sum(likes) // len(likes)
        metrics["avg_likes_sample_size"] = len(likes)
        data_sources["avg_likes"] = "verified"

    # TikTok heartCount
    if "avg_likes" not in metrics:
        m = re.search(r'"heartcount"[:\s]*([\d]+)', text)
        if m:
            metrics["avg_likes"] = _parse_number_from_text(m.group(1))
            data_sources["avg_likes"] = "verified"

    # ── Bio ──
    for pat in [
        r'"biography"[:\s]*"([^"]+)"',
        r'"description"[:\s]*"([^"]+)"',
        r'"signature"[:\s]*"([^"]+)"',
    ]:
        m = re.search(pat, text)
        if m:
            metrics["bio"] = m.group(1)
            break

    # ── Display name from og:title ──
    og_title = re.search(r'og:title["\s]*content="([^"]+)"', content)
    if not og_title:
        og_title = re.search(r'content="([^"]+)"[^>]*og:title', content)
    if og_title:
        raw = og_title.group(1)
        # "Dem Jointz (@demjointz) • Instagram photos and videos" → "Dem Jointz"
        name = re.sub(r"\s*\(.*", "", raw).strip()
        name = re.sub(r"\s*[•·|–-]\s*.*", "", name).strip()
        if name:
            metrics["display_name"] = name

    # ── Estimates (clearly marked) ──

    # Engagement rate estimate when no direct likes available
    if "followers" in metrics and "avg_likes" not in metrics:
        followers = metrics["followers"]
        # Industry average engagement rates from settings
        cfg = Settings()
        rate_map = {
            "instagram": cfg.CREATOR_ENGAGEMENT_RATE_IG,
            "tiktok": cfg.CREATOR_ENGAGEMENT_RATE_TT,
            "youtube": cfg.CREATOR_ENGAGEMENT_RATE_YT,
        }
        rate = rate_map.get(platform, 0.02)
        metrics["avg_likes"] = int(followers * rate)
        metrics["engagement_rate_source"] = "industry_average"
        data_sources["avg_likes"] = "estimated"

    # Posting frequency estimate from total_posts
    if "total_posts" in metrics and "posts_30d" not in metrics:
        total = metrics["total_posts"]
        if total > 0:
            # Conservative estimate: assume account is ~3 years old
            estimated_monthly = max(1, total // 36)
            metrics["posts_30d"] = min(estimated_monthly, 60)
            data_sources["posts_30d"] = "estimated"

    # Following/follower ratio (a real signal)
    if metrics.get("followers") and metrics.get("following"):
        metrics["ff_ratio"] = round(metrics["following"] / metrics["followers"], 3)

    metrics["_data_sources"] = data_sources
    return metrics


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
    display_name: str
    decision: str
    grade: str
    score: float
    score_breakdown: Dict[str, Any]
    data_confidence: Dict[str, str]
    tier_info: Optional[Dict[str, Any]]
    tags: List[str]
    risks: List[str]
    report: str
    raw_profile: Dict[str, Any]
    rag_enhanced: Optional[RAGEnhancedData] = None
    trend: Optional[Dict[str, Any]] = None


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
        handle: str = str(input_data.get("handle", "")).strip().lstrip("@")
        profile_url: Optional[str] = input_data.get("profile_url")
        provided_metrics: Dict[str, Any] = input_data.get("metrics", {}) or {}
        category: Optional[str] = input_data.get("category")

        # Auto-generate profile URL if not provided
        if not profile_url or not profile_url.startswith("http"):
            profile_url = _build_profile_url(platform, handle)
            if profile_url:
                logger.info("Auto-generated profile URL: %s", profile_url)

        # 1) fetch profile via Supadata MCP (preferred) → HttpMCP (fallback)
        profile: Dict[str, Any] = {}
        scraped_metrics: Dict[str, Any] = {}

        if profile_url:
            # Try Supadata MCP first (better at scraping SNS pages)
            try:
                from src.services.supadata_mcp import SupadataMCPClient

                supadata = SupadataMCPClient()
                if supadata.available:
                    results = await supadata.scrape_urls([profile_url])
                    if results:
                        scraped_data = results[0]
                        content_blocks = scraped_data.get("content", [])
                        scraped_text = ""
                        for block in content_blocks:
                            if isinstance(block, dict):
                                scraped_text += block.get("text", "")
                            elif isinstance(block, str):
                                scraped_text += block
                        scraped_metrics = _extract_metrics_from_scraped(
                            scraped_text, platform
                        )
                        profile = {
                            "url": profile_url,
                            "fetched": True,
                            "source": "supadata",
                        }
                        logger.info(
                            "Supadata scraped metrics for @%s: %s",
                            handle,
                            scraped_metrics,
                        )
            except Exception as e:
                logger.info("Supadata MCP failed for %s: %s", profile_url, e)

            # Fallback to HttpMCP if Supadata didn't return useful data
            if not scraped_metrics.get("followers"):
                try:
                    from src.mcp import HttpMCP

                    hmcp = HttpMCP()
                    fetched = hmcp.fetch(profile_url)
                    raw_text = fetched.get("text", "")
                    http_metrics = _extract_metrics_from_scraped(raw_text, platform)
                    if http_metrics:
                        scraped_metrics.update(http_metrics)
                    profile = {
                        "url": profile_url,
                        "fetched": True,
                        "source": "http",
                        "content_type": fetched.get("content_type"),
                    }
                    logger.info(
                        "HttpMCP scraped metrics for @%s: %s", handle, http_metrics
                    )
                except Exception as e:
                    logger.info("HTTP fetch failed for %s: %s", profile_url, e)
                    if not profile:
                        profile = {"url": profile_url, "fetched": False}

        # Merge: provided_metrics override scraped_metrics
        profile.update(scraped_metrics)
        profile.update(provided_metrics)

        # 2) derive signals
        cfg = Settings()
        data_sources: Dict[str, str] = profile.get("_data_sources", {})
        followers = _to_num(
            profile.get("followers") or profile.get("followers_count"), default=0
        )
        following = _to_num(profile.get("following"), default=0)
        total_posts = _to_num(profile.get("total_posts"), default=0)
        avg_likes = _to_num(profile.get("avg_likes"), default=0)
        avg_comments = _to_num(profile.get("avg_comments"), default=0)
        posts_30d = _to_num(profile.get("posts_30d"), default=0)
        reports_90d = _to_num(profile.get("reports_90d"), default=0)
        brand_fit = float(profile.get("brand_fit", 0.0))
        ff_ratio = float(profile.get("ff_ratio", 0.0))
        profile_tags: List[str] = profile.get("tags", []) or []
        display_name = profile.get("display_name", "")

        engagement_rate = _safe_div(avg_likes + 2 * avg_comments, max(1, followers))
        frequency = posts_30d / 30.0

        # ── 3) Tier-based scoring with normalized weights ──
        # Load weights from settings and normalize to sum=1.0
        raw_weights = {
            "followers": cfg.CREATOR_WEIGHT_FOLLOWERS,
            "engagement": cfg.CREATOR_WEIGHT_ENGAGEMENT,
            "activity": cfg.CREATOR_WEIGHT_ACTIVITY,
            "ff_ratio": cfg.CREATOR_WEIGHT_FF_RATIO,
            "brand_fit": cfg.CREATOR_WEIGHT_BRAND_FIT,
        }
        weight_sum = sum(raw_weights.values())
        weights = {k: v / weight_sum for k, v in raw_weights.items()}

        # Influence tier (log-scale, reflects real market value)
        tier_name, s_followers_raw = _classify_tier(followers)
        # Normalize: _classify_tier returns 0~0.40 → scale to 0~1.0 → apply weight
        s_followers = (s_followers_raw / 0.40) * weights["followers"]

        # Engagement score (normalized to weight)
        # Benchmark: platform-specific rates. Scoring relative to benchmark.
        rate_benchmarks = {
            "instagram": cfg.CREATOR_ENGAGEMENT_RATE_IG,
            "tiktok": cfg.CREATOR_ENGAGEMENT_RATE_TT,
            "youtube": cfg.CREATOR_ENGAGEMENT_RATE_YT,
        }
        benchmark_rate = rate_benchmarks.get(platform, 0.02)
        # Score = ratio of actual rate to 2x benchmark (max=1.0)
        # At benchmark rate → 0.5, at 2x benchmark → 1.0
        engage_raw = _zclip(engagement_rate / (2 * benchmark_rate), 0, 1.0)
        s_engage = engage_raw * weights["engagement"]

        # Activity score (normalized to weight)
        # 0.5/day = full score (15 posts/30d)
        freq_raw = _zclip(frequency / 0.5, 0, 1.0)
        s_freq = freq_raw * weights["activity"]

        # FF ratio signal (healthy ratio = low following relative to followers)
        ff_raw = 0.0
        ff_health = "unknown"
        if followers > 0 and following > 0:
            if ff_ratio <= 0.05:
                ff_raw = 1.0
                ff_health = "healthy"
            elif ff_ratio <= 0.15:
                ff_raw = 0.8
                ff_health = "healthy"
            elif ff_ratio <= 0.5:
                ff_raw = 0.5
                ff_health = "moderate"
            elif ff_ratio <= 1.0:
                ff_raw = 0.2
                ff_health = "moderate"
            else:
                ff_raw = 0.0
                ff_health = "unhealthy"
        s_ff = ff_raw * weights["ff_ratio"]

        # Brand fit (external input)
        s_fit = _zclip(brand_fit, 0, 1.0) * weights["brand_fit"]

        base_score = s_followers + s_engage + s_freq + s_ff + s_fit

        # ── Risk penalties (only for confirmed data) ──
        risk_tags: List[str] = []
        if reports_90d >= 3:
            base_score -= 0.15
            risk_tags.append("high_reports")
        if (
            followers > 0
            and engagement_rate < 0.002
            and data_sources.get("avg_likes") == "verified"
        ):
            base_score -= 0.10
            risk_tags.append("low_engagement")
        if (
            posts_30d > 0
            and posts_30d < 4
            and data_sources.get("posts_30d") == "verified"
        ):
            base_score -= 0.05
            risk_tags.append("low_activity")
        if ff_ratio > 1.5 and followers > 0:
            base_score -= 0.05
            risk_tags.append("follow_back_pattern")

        score = float(round(max(0.0, min(1.0, base_score)) * 100, 1))
        grade, decision, tags = _grade_and_decide(score, risk_tags, cfg)

        # ── Build structured score_breakdown with ScoreDetail ──
        max_followers = round(weights["followers"] * 100, 1)
        max_engage = round(weights["engagement"] * 100, 1)
        max_activity = round(weights["activity"] * 100, 1)
        max_ff = round(weights["ff_ratio"] * 100, 1)
        max_fit = round(weights["brand_fit"] * 100, 1)

        score_breakdown: Dict[str, Any] = {
            "followers": {
                "score": round(s_followers * 100, 1),
                "max": max_followers,
                "description": f"{tier_name} — 팔로워 {followers:,}명",
                "source": data_sources.get("followers", "unavailable"),
            },
            "engagement": {
                "score": round(s_engage * 100, 1),
                "max": max_engage,
                "description": (
                    f"참여율 {engagement_rate:.2%}"
                    + (
                        f" (업계 평균 추정)"
                        if data_sources.get("avg_likes") == "estimated"
                        else ""
                    )
                ),
                "source": data_sources.get("avg_likes", "unavailable"),
            },
            "activity": {
                "score": round(s_freq * 100, 1),
                "max": max_activity,
                "description": f"게시 빈도 {frequency:.1f}회/일 (추정 {posts_30d}회/30일)",
                "source": data_sources.get("posts_30d", "unavailable"),
            },
            "ff_ratio": {
                "score": round(s_ff * 100, 1),
                "max": max_ff,
                "description": (
                    f"FF비율 {ff_ratio:.3f} ({ff_health})"
                    if followers > 0 and following > 0
                    else "팔로잉 데이터 없음"
                ),
                "source": data_sources.get("following", "unavailable"),
            },
            "brand_fit": {
                "score": round(s_fit * 100, 1),
                "max": max_fit,
                "description": "브랜드 적합도"
                + (" (미입력)" if brand_fit == 0 else f" {brand_fit:.0%}"),
                "source": "verified" if brand_fit > 0 else "unavailable",
            },
        }

        # ── Build data_confidence map ──
        data_confidence: Dict[str, str] = {
            "followers": data_sources.get("followers", "unavailable"),
            "following": data_sources.get("following", "unavailable"),
            "total_posts": data_sources.get("total_posts", "unavailable"),
            "engagement": data_sources.get("avg_likes", "unavailable"),
            "activity": data_sources.get("posts_30d", "unavailable"),
        }

        # ── Build tier_info ──
        tier_info: Optional[Dict[str, Any]] = {
            "name": tier_name,
            "followers": followers,
            "following": following,
            "total_posts": total_posts,
            "ff_ratio": ff_ratio,
            "ff_health": ff_health,
            "display_name": display_name,
        }

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

        # 5) CreatorHistory trend (if available)
        trend_data: Optional[Dict[str, Any]] = None
        try:
            from src.services.creator_history.service import get_creator_history_service

            history_svc = get_creator_history_service()
            creator_id = handle
            trend_result = await history_svc.get_trend(creator_id)
            if trend_result and trend_result.get("evaluation_count", 0) >= 2:
                trend_data = trend_result
        except Exception as e:
            logger.debug("Trend lookup skipped: %s", e)

        # 6) comprehensive report
        src_label = lambda k: f" [{data_sources.get(k, 'N/A')}]"
        report_parts = [
            f"=== Creator Evaluation Report ===",
            f"Platform: {platform} | Handle: @{handle}",
            f"Display Name: {display_name or 'N/A'}",
            f"Category: {category or 'Not specified'}",
            f"Tier: {tier_name}",
            "",
            f"=== Profile Metrics ===",
            f"Followers: {followers:,}{src_label('followers')}",
            f"Following: {following:,}{src_label('following')}",
            f"Total Posts: {total_posts:,}{src_label('total_posts')}",
            f"FF Ratio: {ff_ratio:.3f} ({ff_health})",
            "",
            f"=== Engagement ===",
            f"Avg Likes: {avg_likes:,}{src_label('avg_likes')}",
            f"Engagement Rate: {engagement_rate:.2%}",
            f"Posts/30d: {posts_30d}{src_label('posts_30d')}",
            f"Posting Freq: {frequency:.1f}/day",
            "",
            f"=== Score Breakdown (weights normalized to 100) ===",
        ]
        for key, detail in score_breakdown.items():
            report_parts.append(
                f"{key}: {detail['score']}/{detail['max']}  — {detail['description']} [{detail['source']}]"
            )
        report_parts.extend(
            [
                f"─────────────────",
                f"Total: {score}/100 → Grade {grade} → {decision.upper()}",
                "",
                f"=== Risks ===",
                f"{'  '.join(risk_tags) if risk_tags else 'None detected'}",
                f"Tags: {', '.join(tags) if tags else 'None'}",
            ]
        )

        # Trend info if available
        if trend_data:
            report_parts.append("")
            report_parts.append("=== Growth Trend ===")
            report_parts.append(f"Trend: {trend_data.get('trend_summary', 'N/A')}")
            fc = trend_data.get("followers_change")
            if fc is not None:
                report_parts.append(f"Follower Change: {fc:+,}")
            sc = trend_data.get("score_change")
            if sc is not None:
                report_parts.append(f"Score Change: {sc:+.1f}")

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
            display_name=display_name,
            decision=decision,
            grade=grade,
            score=score,
            score_breakdown=score_breakdown,
            data_confidence=data_confidence,
            tier_info=tier_info,
            tags=tags,
            risks=risk_tags,
            report=report,
            raw_profile=profile,
            rag_enhanced=rag_enhanced,
            trend=trend_data,
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


def _classify_tier(followers: int) -> tuple[str, float]:
    """Classify creator into influence tier and return (tier_name, raw_score).

    raw_score is on 0~0.40 scale (will be normalized by caller).
    Tiers (industry standard):
      Mega:       1M+     → 0.40
      Macro-Mega: 500K+   → 0.37
      Macro:      100K+   → 0.33
      Mid-Tier:   50K+    → 0.28
      Micro:      10K+    → 0.22
      Nano:       1K+     → 0.14
      Rising:     <1K     → up to 0.08
    """
    if followers >= 1_000_000:
        return "Mega (1M+)", 0.40
    elif followers >= 500_000:
        return "Macro-Mega (500K+)", 0.37
    elif followers >= 100_000:
        return "Macro (100K+)", 0.33
    elif followers >= 50_000:
        return "Mid-Tier (50K+)", 0.28
    elif followers >= 10_000:
        return "Micro (10K+)", 0.22
    elif followers >= 1_000:
        return "Nano (1K+)", 0.14
    else:
        score = _zclip(followers / 1_000 * 0.08, 0, 0.08)
        return "Rising (<1K)", score


def _grade_and_decide(
    score: float, risk_tags: List[str], cfg: Optional[Any] = None
) -> tuple[str, str, List[str]]:
    if cfg is None:
        cfg = Settings()

    # Extended grade system: S/A/B/C/D/F
    if score >= cfg.CREATOR_GRADE_S_THRESHOLD:
        grade = "S"
    elif score >= cfg.CREATOR_GRADE_A_THRESHOLD:
        grade = "A"
    elif score >= cfg.CREATOR_GRADE_B_THRESHOLD:
        grade = "B"
    elif score >= cfg.CREATOR_GRADE_C_THRESHOLD:
        grade = "C"
    elif score >= cfg.CREATOR_GRADE_D_THRESHOLD:
        grade = "D"
    else:
        grade = "F"

    decision = "accept"
    if "high_reports" in risk_tags or score < cfg.CREATOR_REJECT_THRESHOLD:
        decision = "reject"
    elif grade in ("D", "F"):
        decision = "reject"
    elif "low_activity" in risk_tags and score < cfg.CREATOR_GRADE_A_THRESHOLD:
        decision = "hold"

    tags: List[str] = []
    if grade in ("S", "A"):
        tags.append("top_candidate")
    if grade == "F":
        tags.append("data_insufficient")
    if "low_engagement" in risk_tags:
        tags.append("needs_awareness_campaign")
    if "low_activity" in risk_tags:
        tags.append("needs_activation")

    return grade, decision, tags
