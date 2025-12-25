import { MissionDto } from "../api/types";

export const sampleMissions: MissionDto[] = [
  {
    id: "mission_001",
    name: "신제품 언박싱 리뷰",
    type: "content",
    reward_type: "fixed",
    reward_amount: 500000,
    requirement: {
      min_followers: 10000,
      min_engagement_rate: 0.03,
      min_grade: "B",
      allowed_platforms: ["instagram", "tiktok", "youtube"],
      allowed_categories: ["lifestyle", "tech", "beauty"],
      required_tags: ["unboxing"],
    },
  },
  {
    id: "mission_002",
    name: "브랜드 해시태그 챌린지",
    type: "engagement",
    reward_type: "performance",
    reward_amount: 0,
    requirement: {
      min_followers: 5000,
      min_engagement_rate: 0.02,
      min_grade: "C",
      allowed_platforms: ["instagram", "tiktok"],
      allowed_categories: ["lifestyle", "fashion", "beauty", "food"],
      required_tags: ["challenge"],
    },
  },
  {
    id: "mission_003",
    name: "프리미엄 협찬 캠페인",
    type: "branding",
    reward_type: "hybrid",
    reward_amount: 1000000,
    requirement: {
      min_followers: 50000,
      min_engagement_rate: 0.04,
      min_grade: "A",
      allowed_platforms: ["instagram", "youtube"],
      allowed_categories: ["fashion", "beauty", "travel"],
      required_tags: ["premium"],
    },
  },
];

