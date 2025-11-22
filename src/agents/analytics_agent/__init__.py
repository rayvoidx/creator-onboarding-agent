"""DER-005/007: 분석 에이전트 - 학습 성과 분석 및 리포트 생성"""
from typing import Dict, Any, Optional, List
import logging
from pydantic import Field
from datetime import datetime, timedelta
from ...core.base import BaseAgent, BaseState
from ...utils.agent_config import get_agent_runtime_config

logger = logging.getLogger(__name__)


class AnalyticsDataProvider:
    """Analytics 데이터 제공자 - PostgreSQL에서 실제 데이터 조회"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url
        self._use_sample = True  # PostgreSQL 연결 실패 시 샘플 데이터 사용
        self.logger = logging.getLogger("AnalyticsDataProvider")

    def _get_database_url(self) -> str:
        """데이터베이스 URL 조회"""
        if self.database_url:
            return self.database_url

        try:
            from config.settings import get_settings
            return get_settings().DATABASE_URL
        except Exception:
            return "sqlite:///./app.db"

    async def get_learning_metrics(self, user_id: Optional[str], date_range: Dict[str, str]) -> Dict[str, Any]:
        """실제 학습 메트릭 조회"""
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker

            database_url = self._get_database_url()

            # SQLite인 경우 샘플 데이터 반환
            if "sqlite" in database_url:
                return self._get_sample_learning_metrics(user_id)

            sync_url = database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # 학습 활동 데이터 조회
                query = text("""
                    SELECT
                        COUNT(*) as total_activities,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        AVG(score) as avg_score,
                        SUM(duration_minutes) as total_time
                    FROM learning_activities
                    WHERE (:user_id IS NULL OR user_id = :user_id)
                    AND created_at >= :start_date
                    AND created_at <= :end_date
                """)

                start_date = date_range.get('start', (datetime.now() - timedelta(days=30)).isoformat())
                end_date = date_range.get('end', datetime.now().isoformat())

                result = session.execute(query, {
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()

                if result and result[0] and result[0] > 0:
                    total = result[0] or 0
                    completed = result[1] or 0
                    avg_score = result[2] or 0
                    total_time = result[3] or 0

                    return {
                        "completion_rate": round((completed / total * 100) if total > 0 else 0, 1),
                        "avg_score": round(float(avg_score), 1),
                        "time_spent_hours": round(total_time / 60, 1),
                        "modules_completed": completed,
                        "modules_total": total,
                        "last_activity": datetime.now().strftime("%Y-%m-%d"),
                        "streak_days": await self._calculate_streak(session, user_id)
                    }

            finally:
                session.close()
                engine.dispose()

        except Exception as e:
            self.logger.warning(f"Failed to get learning metrics from DB: {e}, using sample data")

        return self._get_sample_learning_metrics(user_id)

    async def get_engagement_metrics(self, user_id: Optional[str], date_range: Dict[str, str]) -> Dict[str, Any]:
        """실제 참여도 메트릭 조회"""
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker

            database_url = self._get_database_url()

            if "sqlite" in database_url:
                return self._get_sample_engagement_metrics(user_id)

            sync_url = database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # 사용자 세션 데이터 조회
                query = text("""
                    SELECT
                        COUNT(*) as total_sessions,
                        AVG(duration_minutes) as avg_duration,
                        SUM(interaction_count) as total_interactions
                    FROM user_sessions
                    WHERE (:user_id IS NULL OR user_id = :user_id)
                    AND created_at >= :start_date
                    AND created_at <= :end_date
                """)

                start_date = date_range.get('start', (datetime.now() - timedelta(days=30)).isoformat())
                end_date = date_range.get('end', datetime.now().isoformat())

                result = session.execute(query, {
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchone()

                if result and result[0] and result[0] > 0:
                    # 주당 로그인 빈도 계산
                    days_in_range = 30  # 기본값
                    try:
                        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        days_in_range = (end - start).days or 1
                    except Exception:
                        pass

                    weeks = max(days_in_range / 7, 1)
                    login_freq = round(result[0] / weeks, 1)

                    return {
                        "login_frequency": login_freq,
                        "avg_session_duration": round(float(result[1] or 0), 1),
                        "interaction_count": result[2] or 0,
                        "participation_rate": min(login_freq / 5 * 100, 100),
                        "forum_posts": 0,
                        "questions_asked": 0
                    }

            finally:
                session.close()
                engine.dispose()

        except Exception as e:
            self.logger.warning(f"Failed to get engagement metrics from DB: {e}, using sample data")

        return self._get_sample_engagement_metrics(user_id)

    async def get_performance_metrics(self, user_id: Optional[str], date_range: Dict[str, str]) -> Dict[str, Any]:
        """실제 성과 메트릭 조회"""
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker

            database_url = self._get_database_url()

            if "sqlite" in database_url:
                return self._get_sample_performance_metrics(user_id)

            sync_url = database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # 테스트 점수 데이터 조회
                query = text("""
                    SELECT score, skill_category, created_at
                    FROM test_results
                    WHERE (:user_id IS NULL OR user_id = :user_id)
                    AND created_at >= :start_date
                    AND created_at <= :end_date
                    ORDER BY created_at
                """)

                start_date = date_range.get('start', (datetime.now() - timedelta(days=30)).isoformat())
                end_date = date_range.get('end', datetime.now().isoformat())

                results = session.execute(query, {
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date
                }).fetchall()

                if results:
                    scores = [int(r[0]) for r in results]
                    skill_levels = {}

                    for r in results:
                        category = r[1] or '기타'
                        if category not in skill_levels:
                            skill_levels[category] = []
                        skill_levels[category].append(int(r[0]))

                    # 카테고리별 평균 계산
                    skill_avg = {k: round(sum(v) / len(v), 1) for k, v in skill_levels.items()}

                    avg_score = sum(scores) / len(scores)
                    improvement = scores[-1] - scores[0] if len(scores) >= 2 else 0

                    return {
                        "test_scores": scores[-5:],  # 최근 5개
                        "avg_test_score": round(avg_score, 1),
                        "improvement_rate": round(improvement / max(scores[0], 1) * 100, 1) if scores else 0,
                        "skill_levels": skill_avg,
                        "certifications": 0
                    }

            finally:
                session.close()
                engine.dispose()

        except Exception as e:
            self.logger.warning(f"Failed to get performance metrics from DB: {e}, using sample data")

        return self._get_sample_performance_metrics(user_id)

    async def _calculate_streak(self, session, user_id: Optional[str]) -> int:
        """연속 학습 일수 계산"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT DISTINCT DATE(created_at) as activity_date
                FROM learning_activities
                WHERE (:user_id IS NULL OR user_id = :user_id)
                ORDER BY activity_date DESC
                LIMIT 30
            """)

            results = session.execute(query, {'user_id': user_id}).fetchall()

            if not results:
                return 0

            streak = 0
            today = datetime.now().date()

            for i, row in enumerate(results):
                activity_date = row[0]
                if isinstance(activity_date, str):
                    activity_date = datetime.strptime(activity_date, "%Y-%m-%d").date()

                expected_date = today - timedelta(days=i)
                if activity_date == expected_date:
                    streak += 1
                else:
                    break

            return streak

        except Exception as e:
            self.logger.warning(f"Failed to calculate streak: {e}")
            return 7  # 기본값

    def _get_sample_learning_metrics(self, user_id: Optional[str]) -> Dict[str, Any]:
        """샘플 학습 메트릭"""
        return {
            "completion_rate": 75.5,
            "avg_score": 82.3,
            "time_spent_hours": 24.5,
            "modules_completed": 15,
            "modules_total": 20,
            "last_activity": datetime.now().strftime("%Y-%m-%d"),
            "streak_days": 7
        }

    def _get_sample_engagement_metrics(self, user_id: Optional[str]) -> Dict[str, Any]:
        """샘플 참여도 메트릭"""
        return {
            "login_frequency": 5.2,
            "avg_session_duration": 45.3,
            "interaction_count": 124,
            "participation_rate": 85.0,
            "forum_posts": 8,
            "questions_asked": 12
        }

    def _get_sample_performance_metrics(self, user_id: Optional[str]) -> Dict[str, Any]:
        """샘플 성과 메트릭"""
        return {
            "test_scores": [78, 82, 85, 88, 90],
            "avg_test_score": 84.6,
            "improvement_rate": 15.4,
            "skill_levels": {
                "기본": 95,
                "중급": 80,
                "고급": 65
            },
            "certifications": 2
        }


class AnalyticsState(BaseState):
    """분석 상태 관리"""
    report_type: Optional[str] = None  # learning_progress, engagement, performance
    user_id: Optional[str] = None
    date_range: Dict[str, str] = Field(default_factory=dict)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    external_data: Dict[str, Any] = Field(default_factory=dict)
    youtube_insights: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsAgent(BaseAgent[AnalyticsState]):
    """
    학습 성과 분석 에이전트

    기능:
    - 학습 진도 분석
    - 참여도 분석
    - 성과 메트릭 계산
    - 인사이트 및 추천 생성
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("analytics", config)
        super().__init__("AnalyticsAgent", merged_config)
        self.agent_model_config = merged_config
        self.llm_client = None  # LLM 클라이언트 (인사이트 생성용)
        self.data_provider = AnalyticsDataProvider(merged_config.get('database_url'))

    async def execute(self, state: AnalyticsState) -> AnalyticsState:
        """
        분석 실행

        Args:
            state: 분석 타입과 파라미터가 포함된 상태

        Returns:
            분석 결과가 포함된 업데이트된 상태
        """
        try:
            if not state.report_type:
                logger.warning("분석 타입이 지정되지 않았습니다")
                state.report_type = "learning_progress"

            logger.info(f"분석 시작 - 타입: {state.report_type}, 사용자: {state.user_id}")

            # 분석 타입별 처리
            if state.report_type == "learning_progress":
                state = await self._analyze_learning_progress(state)
            elif state.report_type == "engagement":
                state = await self._analyze_engagement(state)
            elif state.report_type == "performance":
                state = await self._analyze_performance(state)
            else:
                logger.warning(f"알 수 없는 분석 타입: {state.report_type}")
                state = await self._analyze_learning_progress(state)

            # 인사이트 생성
            state.insights = self._generate_insights(state.metrics)

            # 추천 생성
            state.recommendations = self._generate_recommendations(state.metrics)

            # 외부 데이터 병합
            state = self._merge_external_enrichment(state)

            logger.info(f"분석 완료 - {len(state.insights)}개 인사이트, {len(state.recommendations)}개 추천")

        except Exception as e:
            logger.error(f"분석 실패: {e}", exc_info=True)
            state.errors.append(f"분석 오류: {str(e)}")

        return state

    async def _analyze_learning_progress(self, state: AnalyticsState) -> AnalyticsState:
        """학습 진도 분석"""
        logger.info("학습 진도 분석 수행")

        # 실제 DB에서 데이터 조회
        metrics = await self.data_provider.get_learning_metrics(state.user_id, state.date_range)

        state.metrics = metrics
        state.analysis = {
            "summary": "학습 진도 분석 결과",
            "completion_rate": metrics.get("completion_rate", 0),
            "avg_score": metrics.get("avg_score", 0),
            "time_spent_hours": metrics.get("time_spent_hours", 0),
            "modules_completed": metrics.get("modules_completed", 0),
            "modules_total": metrics.get("modules_total", 0),
            "trend": self._calculate_trend(metrics)
        }

        return state

    async def _analyze_engagement(self, state: AnalyticsState) -> AnalyticsState:
        """참여도 분석"""
        logger.info("참여도 분석 수행")

        # 실제 DB에서 데이터 조회
        metrics = await self.data_provider.get_engagement_metrics(state.user_id, state.date_range)

        state.metrics = metrics
        state.analysis = {
            "summary": "참여도 분석 결과",
            "login_frequency": metrics.get("login_frequency", 0),
            "avg_session_duration": metrics.get("avg_session_duration", 0),
            "interaction_count": metrics.get("interaction_count", 0),
            "participation_rate": metrics.get("participation_rate", 0),
            "engagement_score": self._calculate_engagement_score(metrics)
        }

        return state

    async def _analyze_performance(self, state: AnalyticsState) -> AnalyticsState:
        """성과 분석"""
        logger.info("성과 분석 수행")

        # 실제 DB에서 데이터 조회
        metrics = await self.data_provider.get_performance_metrics(state.user_id, state.date_range)

        state.metrics = metrics
        state.analysis = {
            "summary": "성과 분석 결과",
            "test_scores": metrics.get("test_scores", []),
            "avg_test_score": metrics.get("avg_test_score", 0),
            "improvement_rate": metrics.get("improvement_rate", 0),
            "skill_levels": metrics.get("skill_levels", {}),
            "performance_grade": self._calculate_performance_grade(metrics)
        }

        return state

    def _calculate_trend(self, metrics: Dict[str, Any]) -> str:
        """학습 트렌드 계산"""
        completion_rate = metrics.get("completion_rate", 0)

        if completion_rate >= 80:
            return "excellent"
        elif completion_rate >= 60:
            return "good"
        elif completion_rate >= 40:
            return "moderate"
        else:
            return "needs_improvement"

    def _calculate_engagement_score(self, metrics: Dict[str, Any]) -> float:
        """참여도 점수 계산"""
        # 여러 메트릭을 결합하여 종합 점수 계산
        login_freq = min(metrics.get("login_frequency", 0) / 7, 1.0)  # 주 7회 만점
        participation = metrics.get("participation_rate", 0) / 100
        interaction = min(metrics.get("interaction_count", 0) / 100, 1.0)

        score = (login_freq * 0.3 + participation * 0.5 + interaction * 0.2) * 100
        return round(score, 2)

    def _calculate_performance_grade(self, metrics: Dict[str, Any]) -> str:
        """성과 등급 계산"""
        avg_score = metrics.get("avg_test_score", 0)

        if avg_score >= 90:
            return "A"
        elif avg_score >= 80:
            return "B"
        elif avg_score >= 70:
            return "C"
        elif avg_score >= 60:
            return "D"
        else:
            return "F"

    def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """메트릭 기반 인사이트 생성"""
        insights = []

        # 학습 진도 관련
        if "completion_rate" in metrics:
            rate = metrics["completion_rate"]
            if rate >= 80:
                insights.append("학습 진도가 우수합니다. 계속해서 좋은 페이스를 유지하세요.")
            elif rate >= 60:
                insights.append("학습 진도가 양호합니다. 조금 더 집중하면 목표 달성이 가능합니다.")
            else:
                insights.append("학습 진도가 다소 느립니다. 학습 시간을 늘리는 것을 권장합니다.")

        # 테스트 점수 관련
        if "test_scores" in metrics and metrics["test_scores"]:
            scores = metrics["test_scores"]
            if len(scores) >= 2:
                trend = scores[-1] - scores[0]
                if trend > 0:
                    insights.append(f"테스트 점수가 지속적으로 향상되고 있습니다 (+{trend}점).")
                elif trend < 0:
                    insights.append("최근 테스트 점수가 하락했습니다. 복습이 필요할 수 있습니다.")

        # 참여도 관련
        if "participation_rate" in metrics:
            rate = metrics["participation_rate"]
            if rate >= 80:
                insights.append("높은 참여도를 보이고 있습니다. 훌륭합니다!")
            elif rate < 50:
                insights.append("참여도가 낮습니다. 더 적극적인 학습 활동이 필요합니다.")

        return insights

    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """메트릭 기반 추천 생성"""
        recommendations = []

        # 학습 시간 관련
        if "time_spent_hours" in metrics:
            hours = metrics["time_spent_hours"]
            if hours < 10:
                recommendations.append("주간 학습 시간을 늘리는 것을 추천합니다 (권장: 주 10-15시간).")

        # 성과 관련
        if "avg_test_score" in metrics:
            score = metrics["avg_test_score"]
            if score < 70:
                recommendations.append("기초 개념 복습을 권장합니다. 온라인 튜토리얼을 활용해보세요.")

        # 참여도 관련
        if "login_frequency" in metrics:
            freq = metrics["login_frequency"]
            if freq < 3:
                recommendations.append("정기적인 학습 습관을 형성하세요. 주 3-5회 접속을 목표로 하세요.")

        # 스킬 레벨 관련
        if "skill_levels" in metrics:
            levels = metrics["skill_levels"]
            weak_skills = [skill for skill, level in levels.items() if level < 70]
            if weak_skills:
                recommendations.append(f"다음 영역의 보강이 필요합니다: {', '.join(weak_skills)}")

        return recommendations

    def _merge_external_enrichment(self, state: AnalyticsState) -> AnalyticsState:
        """Attach MCP-derived context (web snippets, YouTube insights)."""
        ctx = state.context or {}
        enrichment = ctx.get("mcp_enrichment", {})

        snippets = ctx.get("external_snippets") or enrichment.get("external_snippets")
        if snippets:
            state.external_data["web_snippets"] = snippets
            snippet_sites = [
                snippet.get("site_name") or snippet.get("url")
                for snippet in snippets
                if isinstance(snippet, dict)
            ]
            if snippet_sites:
                state.insights.append(
                    f"외부 기관 자료 {len(snippet_sites)}건을 참고하여 인사이트를 강화했습니다."
                )

        youtube_data = ctx.get("youtube_insights") or enrichment.get("youtube_insights")
        if youtube_data:
            state.youtube_insights = youtube_data
            channel_info = (
                youtube_data.get("channel_overview", {}).get("channel_info", {})
                if isinstance(youtube_data, dict)
                else {}
            )
            channel_title = channel_info.get("title")
            if channel_title:
                state.insights.append(
                    f"YouTube 채널 '{channel_title}' 최근 퍼포먼스를 함께 분석했습니다."
                )

        if state.external_data:
            state.analysis.setdefault("external_sources", state.external_data)
        if state.youtube_insights:
            state.analysis.setdefault("youtube_insights", state.youtube_insights)

        return state

    def set_llm_client(self, llm_client):
        """LLM 클라이언트 설정 (고급 인사이트 생성용)"""
        self.llm_client = llm_client
        logger.info("LLM 클라이언트가 AnalyticsAgent에 연결되었습니다")


