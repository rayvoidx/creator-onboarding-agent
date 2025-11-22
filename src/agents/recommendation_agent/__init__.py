"""DER-002: 맞춤형 추천 에이전트"""
import logging
from typing import Dict, Any, Optional, List
from pydantic import Field
from ...core.base import BaseAgent, BaseState

logger = logging.getLogger(__name__)


class RecommendationState(BaseState):
    """추천 상태 관리"""
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    user_profile: Optional[Dict[str, Any]] = None
    learning_preferences: Optional[Dict[str, Any]] = None
    competency_data: Optional[Dict[str, Any]] = None


class RecommendationAgent(BaseAgent[RecommendationState]):
    """추천 에이전트"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("RecommendationAgent", config)
        self.learning_materials = self._initialize_learning_materials()
        self.recommendation_weights = {
            'competency_level': 0.4,
            'learning_style': 0.3,
            'interests': 0.2,
            'difficulty': 0.1
        }

    def _initialize_learning_materials(self) -> List[Dict[str, Any]]:
        """학습 자료 초기화"""
        return [
            {
                "id": "mat_001",
                "title": "기초 육아 이론",
                "type": "video",
                "difficulty": "beginner",
                "duration": 30,
                "topics": ["육아기초", "발달이론"],
                "rating": 4.5,
                "description": "육아의 기본 원리와 이론을 학습합니다."
            },
            {
                "id": "mat_002", 
                "title": "아동 발달 단계별 이해",
                "type": "interactive",
                "difficulty": "intermediate",
                "duration": 45,
                "topics": ["발달단계", "인지발달"],
                "rating": 4.7,
                "description": "아동의 발달 단계를 체계적으로 이해합니다."
            },
            {
                "id": "mat_003",
                "title": "부모-자녀 소통 기법",
                "type": "workshop",
                "difficulty": "advanced",
                "duration": 60,
                "topics": ["소통", "심리학"],
                "rating": 4.8,
                "description": "효과적인 부모-자녀 소통 방법을 학습합니다."
            },
            {
                "id": "mat_004",
                "title": "디지털 시대의 육아",
                "type": "article",
                "difficulty": "intermediate",
                "duration": 20,
                "topics": ["디지털육아", "미디어"],
                "rating": 4.3,
                "description": "디지털 환경에서의 현대적 육아 방법을 다룹니다."
            },
            {
                "id": "mat_005",
                "title": "아동 안전 관리",
                "type": "video",
                "difficulty": "beginner",
                "duration": 25,
                "topics": ["안전", "응급처치"],
                "rating": 4.6,
                "description": "아동의 안전을 위한 실용적인 관리 방법을 학습합니다."
            }
        ]

    async def execute(self, state: RecommendationState) -> RecommendationState:
        """추천 실행"""
        try:
            state = await self.pre_execute(state)
            
            # 사용자 프로필 분석
            user_profile = state.user_profile or {}
            learning_preferences = state.learning_preferences or {}
            competency_data = state.competency_data or {}
            
            # 추천 생성
            recommendations = await self._generate_recommendations(
                user_profile, learning_preferences, competency_data
            )
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(
                user_profile, learning_preferences, competency_data
            )
            
            state.recommendations = recommendations
            state.confidence = confidence
            
            state = await self.post_execute(state)
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            state.add_error(f"추천 생성 실패: {str(e)}")
            
        return state

    async def _generate_recommendations(
        self, 
        user_profile: Dict[str, Any], 
        learning_preferences: Dict[str, Any],
        competency_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """추천 생성"""
        try:
            # 역량 수준 파악
            competency_level = self._assess_competency_level(competency_data)
            
            # 학습 스타일 파악
            learning_style = learning_preferences.get('style', 'balanced')
            
            # 관심사 파악
            interests = user_profile.get('interests', [])
            
            # 추천 점수 계산
            scored_materials = []
            for material in self.learning_materials:
                score = self._calculate_recommendation_score(
                    material, competency_level, learning_style, interests
                )
                scored_materials.append((material, score))
            
            # 점수순 정렬 및 상위 3개 선택
            scored_materials.sort(key=lambda x: x[1], reverse=True)
            top_recommendations = scored_materials[:3]
            
            # 추천 결과 포맷팅
            recommendations = []
            for material, score in top_recommendations:
                recommendation = {
                    "material_id": material["id"],
                    "title": material["title"],
                    "type": material["type"],
                    "difficulty": material["difficulty"],
                    "duration": material["duration"],
                    "rating": material["rating"],
                    "description": material["description"],
                    "recommendation_score": score,
                    "reason": self._generate_recommendation_reason(
                        material, competency_level, learning_style
                    )
                }
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            return []

    def _assess_competency_level(self, competency_data: Dict[str, Any]) -> str:
        """역량 수준 평가"""
        if not competency_data:
            return "beginner"
        
        score = competency_data.get('competency_score', 0.0)
        if score >= 0.8:
            return "advanced"
        elif score >= 0.6:
            return "intermediate"
        else:
            return "beginner"

    def _calculate_recommendation_score(
        self, 
        material: Dict[str, Any], 
        competency_level: str,
        learning_style: str,
        interests: List[str]
    ) -> float:
        """추천 점수 계산"""
        score = 0.0
        
        # 난이도 매칭 (40% 가중치)
        difficulty_match = self._get_difficulty_match_score(material['difficulty'], competency_level)
        score += difficulty_match * self.recommendation_weights['competency_level']
        
        # 학습 스타일 매칭 (30% 가중치)
        style_match = self._get_style_match_score(material['type'], learning_style)
        score += style_match * self.recommendation_weights['learning_style']
        
        # 관심사 매칭 (20% 가중치)
        interest_match = self._get_interest_match_score(material['topics'], interests)
        score += interest_match * self.recommendation_weights['interests']
        
        # 평점 (10% 가중치)
        rating_score = material['rating'] / 5.0
        score += rating_score * self.recommendation_weights['difficulty']
        
        return min(score, 1.0)

    def _get_difficulty_match_score(self, material_difficulty: str, user_level: str) -> float:
        """난이도 매칭 점수"""
        difficulty_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
        material_level = difficulty_map.get(material_difficulty, 1)
        user_level_num = difficulty_map.get(user_level, 1)
        
        # 사용자 수준과 비슷하거나 약간 높은 난이도 선호
        diff = abs(material_level - user_level_num)
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.8
        else:
            return 0.3

    def _get_style_match_score(self, material_type: str, learning_style: str) -> float:
        """학습 스타일 매칭 점수"""
        style_preferences = {
            "visual": {"video": 1.0, "interactive": 0.8, "article": 0.3, "workshop": 0.6},
            "auditory": {"video": 0.8, "interactive": 0.6, "article": 0.2, "workshop": 1.0},
            "kinesthetic": {"video": 0.4, "interactive": 1.0, "article": 0.2, "workshop": 0.9},
            "balanced": {"video": 0.7, "interactive": 0.8, "article": 0.6, "workshop": 0.8}
        }
        
        return style_preferences.get(learning_style, {}).get(material_type, 0.5)

    def _get_interest_match_score(self, material_topics: List[str], user_interests: List[str]) -> float:
        """관심사 매칭 점수"""
        if not user_interests:
            return 0.5
        
        matches = len(set(material_topics) & set(user_interests))
        return min(matches / len(user_interests), 1.0)

    def _calculate_confidence(
        self, 
        user_profile: Dict[str, Any], 
        learning_preferences: Dict[str, Any],
        competency_data: Dict[str, Any]
    ) -> float:
        """신뢰도 계산"""
        confidence = 0.5  # 기본값
        
        # 사용자 프로필 완성도
        if user_profile:
            profile_completeness = len([v for v in user_profile.values() if v]) / max(len(user_profile), 1)
            confidence += profile_completeness * 0.2
        
        # 학습 선호도 정보
        if learning_preferences:
            confidence += 0.2
        
        # 역량 데이터 존재
        if competency_data:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _generate_recommendation_reason(
        self, 
        material: Dict[str, Any], 
        competency_level: str,
        learning_style: str
    ) -> str:
        """추천 이유 생성"""
        reasons = []
        
        if material['difficulty'] == competency_level:
            reasons.append("현재 수준에 적합한 난이도")
        elif material['difficulty'] == 'intermediate' and competency_level == 'beginner':
            reasons.append("다음 단계로 도전할 수 있는 내용")
        
        if material['type'] == 'video' and learning_style in ['visual', 'balanced']:
            reasons.append("시각적 학습에 효과적")
        elif material['type'] == 'workshop' and learning_style in ['kinesthetic', 'auditory']:
            reasons.append("실습과 토론이 포함된 학습")
        
        if material['rating'] >= 4.5:
            reasons.append("높은 만족도")
        
        return "; ".join(reasons) if reasons else "개인화된 추천"


