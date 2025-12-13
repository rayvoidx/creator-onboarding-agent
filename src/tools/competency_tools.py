"""역량 진단 도구"""

import hashlib
import json
from typing import List, Any, Dict, Optional
import logging

# 선택적 ML 의존성
try:
    import numpy as np  # type: ignore
    from sklearn.preprocessing import StandardScaler  # type: ignore
    from sklearn.ensemble import RandomForestClassifier  # type: ignore

    ML_AVAILABLE = True
except ImportError:
    np = None  # type: ignore
    StandardScaler = None  # type: ignore
    RandomForestClassifier = None  # type: ignore
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)


class CompetencyAnalyzer:
    """역량 분석기"""

    def __init__(self):
        if ML_AVAILABLE and StandardScaler and RandomForestClassifier:
            self.scaler = StandardScaler()
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.is_trained = False
        else:
            self.scaler = None  # type: ignore
            self.model = None  # type: ignore
            self.is_trained = False
            logger.warning("ML libraries not available. Using fallback mode.")

    async def analyze(self, data: Any) -> Dict[str, Any]:
        """역량 분석"""
        try:
            if isinstance(data, dict) and "responses" in data:
                responses = data["responses"]
                if not responses:
                    return {"result": "no_data", "competency_score": 0.0}

                # 응답 데이터를 벡터로 변환
                features = self._extract_features(responses)

                # 역량 점수 계산
                competency_score = self._calculate_competency_score(features)

                # 분석 결과 생성
                result = {
                    "competency_score": competency_score,
                    "level": self._get_competency_level(competency_score),
                    "strengths": self._identify_strengths(features),
                    "improvement_areas": self._identify_improvement_areas(features),
                    "recommendations": self._generate_recommendations(competency_score),
                }

                return result
            else:
                return {"result": "invalid_data", "competency_score": 0.0}

        except Exception as e:
            logger.error(f"Competency analysis failed: {e}")
            return {"result": "error", "competency_score": 0.0, "error": str(e)}

    def _extract_features(self, responses: List[Dict[str, Any]]) -> Any:
        """응답에서 특징 추출"""
        features = []
        for response in responses:
            if "score" in response:
                features.append(response["score"])
            elif "rating" in response:
                features.append(response["rating"])
            else:
                features.append(0.5)  # 기본값

        if ML_AVAILABLE and np is not None:
            return np.array(features).reshape(-1, 1)
        else:
            return [[f] for f in features]  # List[List[float]] fallback

    def _calculate_competency_score(self, features: Any) -> float:
        """역량 점수 계산"""
        if not features or len(features) == 0:
            return 0.0

        # 평균 점수 계산
        if ML_AVAILABLE and np is not None:
            avg_score = np.mean(features)
        else:
            # Fallback: 수동 평균 계산
            flat = [f[0] if isinstance(f, list) else f for f in features]
            avg_score = sum(flat) / len(flat) if flat else 0.0

        # 정규화 (0-1 범위)
        normalized_score = min(max(avg_score, 0.0), 1.0)

        return float(normalized_score)

    def _get_competency_level(self, score: float) -> str:
        """역량 수준 판정"""
        if score >= 0.8:
            return "고급"
        elif score >= 0.6:
            return "중급"
        elif score >= 0.4:
            return "초급"
        else:
            return "기초"

    def _identify_strengths(self, features: Any) -> List[str]:
        """강점 식별"""
        strengths = []
        if not features or len(features) == 0:
            return strengths

        if ML_AVAILABLE and np is not None:
            high_scores = features[features > 0.7]
            if len(high_scores) > 0:
                strengths.append("높은 학습 성취도")
            if np.mean(features) > 0.6:
                strengths.append("일관된 성과")
        else:
            # Fallback
            flat = [f[0] if isinstance(f, list) else f for f in features]
            high_scores = [s for s in flat if s > 0.7]
            if len(high_scores) > 0:
                strengths.append("높은 학습 성취도")
            if sum(flat) / len(flat) > 0.6:
                strengths.append("일관된 성과")
        return strengths

    def _identify_improvement_areas(self, features: Any) -> List[str]:
        """개선 영역 식별"""
        areas = []
        if not features or len(features) == 0:
            return areas

        if ML_AVAILABLE and np is not None:
            low_scores = features[features < 0.4]
            if len(low_scores) > 0:
                areas.append("기초 역량 강화")
            if np.std(features) > 0.3:
                areas.append("일관성 개선")
        else:
            # Fallback
            flat = [f[0] if isinstance(f, list) else f for f in features]
            low_scores = [s for s in flat if s < 0.4]
            if len(low_scores) > 0:
                areas.append("기초 역량 강화")
            # Simple std calculation
            mean = sum(flat) / len(flat) if flat else 0
            variance = sum((x - mean) ** 2 for x in flat) / len(flat) if flat else 0
            std = variance**0.5
            if std > 0.3:
                areas.append("일관성 개선")
        return areas

    def _generate_recommendations(self, score: float) -> List[str]:
        """추천사항 생성"""
        recommendations = []
        if score < 0.4:
            recommendations.append("기초 학습 자료 추천")
            recommendations.append("개별 맞춤형 학습 계획 수립")
        elif score < 0.7:
            recommendations.append("심화 학습 과정 추천")
            recommendations.append("실습 기회 확대")
        else:
            recommendations.append("전문가 수준 학습 자료 추천")
            recommendations.append("멘토링 프로그램 참여")

        return recommendations


class SecurityTool:
    """보안 도구"""

    def __init__(self):
        self.encryption_key = "default_key"  # 실제로는 환경변수에서 가져와야 함

    async def anonymize_personal_data(self, data: List[Any]) -> List[Any]:
        """개인정보 익명화"""
        try:
            anonymized_data = []
            for item in data:
                if isinstance(item, dict):
                    anonymized_item = item.copy()
                    # 개인정보 필드 익명화
                    for key in ["name", "email", "phone", "id"]:
                        if key in anonymized_item:
                            anonymized_item[key] = self._hash_value(
                                str(anonymized_item[key])
                            )
                    anonymized_data.append(anonymized_item)
                else:
                    anonymized_data.append(item)
            return anonymized_data
        except Exception as e:
            logger.error(f"Data anonymization failed: {e}")
            return data

    async def encrypt_sensitive_data(self, data: Dict[str, Any]) -> str:
        """민감 데이터 암호화"""
        try:
            # 간단한 해시 기반 암호화 (실제로는 더 강력한 암호화 사용)
            data_str = json.dumps(data, sort_keys=True)
            encrypted = hashlib.sha256(
                (data_str + self.encryption_key).encode()
            ).hexdigest()
            return encrypted
        except Exception as e:
            logger.error(f"Data encryption failed: {e}")
            return "encryption_failed"

    def _hash_value(self, value: str) -> str:
        """값 해시화"""
        return hashlib.md5(value.encode()).hexdigest()[:8]
