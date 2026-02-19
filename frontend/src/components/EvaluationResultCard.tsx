import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { CreatorEvaluationResponse, ScoreDetail } from "../api/types";
import { Badge } from "./ui/badge";

interface EvaluationResultCardProps {
  loading: boolean;
  result?: CreatorEvaluationResponse;
}

const GRADE_COLORS: Record<string, string> = {
  S: "#f59e0b",
  A: "#10b981",
  B: "#3b82f6",
  C: "#6b7280",
  D: "#ef4444",
  F: "#991b1b",
};

const GRADE_THRESHOLDS = [
  { grade: "S", min: 85 },
  { grade: "A", min: 70 },
  { grade: "B", min: 55 },
  { grade: "C", min: 40 },
  { grade: "D", min: 30 },
  { grade: "F", min: 0 },
];

function ConfidenceBadge({ source }: { source: string }) {
  const { t } = useTranslation();

  if (source === "verified") {
    return (
      <Tooltip title={t("evaluation.verifiedTooltip")} arrow>
        <Chip
          icon={<CheckCircleOutlineIcon sx={{ fontSize: 14 }} />}
          label={t("evaluation.verified")}
          size="small"
          sx={{
            bgcolor: "rgba(16, 185, 129, 0.15)",
            color: "#10b981",
            fontSize: "0.7rem",
            height: 22,
          }}
        />
      </Tooltip>
    );
  }

  if (source === "estimated") {
    return (
      <Tooltip title={t("evaluation.estimatedTooltip")} arrow>
        <Chip
          icon={<HelpOutlineIcon sx={{ fontSize: 14 }} />}
          label={t("evaluation.estimated")}
          size="small"
          sx={{
            bgcolor: "rgba(245, 158, 11, 0.15)",
            color: "#f59e0b",
            fontSize: "0.7rem",
            height: 22,
          }}
        />
      </Tooltip>
    );
  }

  return (
    <Tooltip title={t("evaluation.unavailableTooltip")} arrow>
      <Chip
        icon={<LockOutlinedIcon sx={{ fontSize: 14 }} />}
        label={t("evaluation.unavailable")}
        size="small"
        sx={{
          bgcolor: "rgba(107, 114, 128, 0.15)",
          color: "#6b7280",
          fontSize: "0.7rem",
          height: 22,
        }}
      />
    </Tooltip>
  );
}

function ScoreBar({ label, detail }: { label: string; detail: ScoreDetail }) {
  const pct = detail.max > 0 ? (detail.score / detail.max) * 100 : 0;

  return (
    <Box sx={{ mb: 1.5 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 0.5,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" fontWeight={600} sx={{ minWidth: 90 }}>
            {label}
          </Typography>
          <ConfidenceBadge source={detail.source} />
        </Box>
        <Typography variant="body2" color="text.secondary">
          {detail.score}/{detail.max}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={Math.min(pct, 100)}
        sx={{
          height: 8,
          borderRadius: 4,
          bgcolor: "rgba(255,255,255,0.06)",
          "& .MuiLinearProgress-bar": {
            borderRadius: 4,
            bgcolor:
              pct >= 80
                ? "#10b981"
                : pct >= 50
                  ? "#3b82f6"
                  : pct >= 20
                    ? "#f59e0b"
                    : "#ef4444",
          },
        }}
      />
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 0.25, display: "block" }}
      >
        {detail.description}
      </Typography>
    </Box>
  );
}

function GradeGauge({ score, grade }: { score: number; grade: string }) {
  const { t } = useTranslation();
  const color = GRADE_COLORS[grade] || "#6b7280";

  return (
    <Box>
      <Box sx={{ position: "relative", mb: 1 }}>
        <Box
          sx={{
            height: 12,
            borderRadius: 6,
            bgcolor: "rgba(255,255,255,0.06)",
            overflow: "hidden",
            display: "flex",
          }}
        >
          {GRADE_THRESHOLDS.map((g, i) => {
            const nextMin =
              i > 0 ? GRADE_THRESHOLDS[i - 1].min : 100;
            const width = nextMin - g.min;
            return (
              <Box
                key={g.grade}
                sx={{
                  width: `${width}%`,
                  bgcolor:
                    g.grade === grade
                      ? GRADE_COLORS[g.grade]
                      : `${GRADE_COLORS[g.grade]}33`,
                  borderRight:
                    i < GRADE_THRESHOLDS.length - 1
                      ? "1px solid rgba(0,0,0,0.3)"
                      : "none",
                }}
              />
            );
          })}
        </Box>
        <Box
          sx={{
            position: "absolute",
            left: `${Math.min(score, 100)}%`,
            top: -2,
            transform: "translateX(-50%)",
            width: 16,
            height: 16,
            borderRadius: "50%",
            bgcolor: color,
            border: "2px solid #fff",
            boxShadow: `0 0 6px ${color}80`,
          }}
        />
      </Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", px: 0.5 }}>
        {GRADE_THRESHOLDS.slice()
          .reverse()
          .map((g) => (
            <Typography
              key={g.grade}
              variant="caption"
              sx={{
                color:
                  g.grade === grade ? GRADE_COLORS[g.grade] : "text.disabled",
                fontWeight: g.grade === grade ? 700 : 400,
              }}
            >
              {g.grade}
            </Typography>
          ))}
      </Box>
      <Tooltip
        title={
          <Box>
            <Typography variant="caption">
              {t("evaluation.gradeS")}
            </Typography>
            <br />
            <Typography variant="caption">
              {t("evaluation.gradeA")}
            </Typography>
            <br />
            <Typography variant="caption">
              {t("evaluation.gradeB")}
            </Typography>
            <br />
            <Typography variant="caption">
              {t("evaluation.gradeC")}
            </Typography>
            <br />
            <Typography variant="caption">
              {t("evaluation.gradeD")}
            </Typography>
            <br />
            <Typography variant="caption">
              {t("evaluation.gradeF")}
            </Typography>
          </Box>
        }
        arrow
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ cursor: "help", mt: 0.5, display: "inline-block" }}
        >
          {t("evaluation.gradeScale")}
        </Typography>
      </Tooltip>
    </Box>
  );
}

function TrendIcon({ summary }: { summary: string }) {
  if (summary === "improving")
    return <TrendingUpIcon sx={{ color: "#10b981", fontSize: 18 }} />;
  if (summary === "declining")
    return <TrendingDownIcon sx={{ color: "#ef4444", fontSize: 18 }} />;
  return <TrendingFlatIcon sx={{ color: "#6b7280", fontSize: 18 }} />;
}

export default function EvaluationResultCard({
  loading,
  result,
}: EvaluationResultCardProps) {
  const { t } = useTranslation();

  const breakdownEntries = result
    ? Object.entries(result.score_breakdown || {})
    : [];

  return (
    <Card sx={{ height: "100%" }}>
      <CardHeader
        title={t("evaluation.resultCardTitle")}
        subheader={t("evaluation.resultCardSubtitle")}
      />
      <CardContent sx={{ height: "100%" }}>
        {loading && (
          <Stack
            alignItems="center"
            justifyContent="center"
            spacing={2}
            minHeight={220}
          >
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              {t("common.evaluating")}
            </Typography>
          </Stack>
        )}

        {!loading && !result && (
          <Alert severity="info">{t("evaluation.infoPlaceholder")}</Alert>
        )}

        {result && (
          <Stack spacing={3}>
            {/* Header: Platform, Handle, Display Name, Decision */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: 1,
              }}
            >
              <Box className="space-y-1">
                <Typography variant="h5">
                  {result.display_name || `@${result.handle}`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {result.platform} · @{result.handle}
                </Typography>
                <Badge variant="default" className="bg-white/10 text-white/80">
                  {t("common.decision")} · {result.decision}
                </Badge>
              </Box>
              <Box sx={{ textAlign: "right" }}>
                <Typography variant="overline" color="text.secondary">
                  {t("evaluation.grade")}
                </Typography>
                <Typography
                  variant="h2"
                  sx={{ color: GRADE_COLORS[result.grade] || "#6b7280" }}
                >
                  {result.grade}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  {result.score}/100
                </Typography>
              </Box>
            </Box>

            {/* Tier Info Card */}
            {result.tier && (
              <Box
                sx={{
                  borderRadius: 2,
                  p: 2,
                  border: "1px solid rgba(255,255,255,0.08)",
                  bgcolor: "rgba(255,255,255,0.02)",
                }}
              >
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {t("evaluation.tier")}: {result.tier.name}
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                    gap: 1.5,
                  }}
                >
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("evaluation.followers")}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {result.tier.followers.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("evaluation.following")}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {result.tier.following.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("evaluation.totalPosts")}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {result.tier.total_posts.toLocaleString()}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t("evaluation.ffRatio")}
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {result.tier.ff_ratio.toFixed(3)}{" "}
                      <Chip
                        label={result.tier.ff_health}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: "0.65rem",
                          bgcolor:
                            result.tier.ff_health === "healthy"
                              ? "rgba(16,185,129,0.15)"
                              : result.tier.ff_health === "moderate"
                                ? "rgba(245,158,11,0.15)"
                                : "rgba(239,68,68,0.15)",
                          color:
                            result.tier.ff_health === "healthy"
                              ? "#10b981"
                              : result.tier.ff_health === "moderate"
                                ? "#f59e0b"
                                : "#ef4444",
                        }}
                      />
                    </Typography>
                  </Box>
                </Box>
              </Box>
            )}

            {/* Grade Gauge */}
            <Box>
              <GradeGauge score={result.score} grade={result.grade} />
            </Box>

            {/* Score Breakdown with criteria descriptions */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
                {t("common.scoreDetail")}
              </Typography>
              {breakdownEntries.map(([label, detail]) => {
                const d = detail as ScoreDetail;
                if (!d || typeof d !== "object") return null;
                return <ScoreBar key={label} label={label} detail={d} />;
              })}
            </Box>

            {/* Trend */}
            {result.trend && (
              <Box
                sx={{
                  borderRadius: 2,
                  p: 1.5,
                  border: "1px solid rgba(255,255,255,0.08)",
                  bgcolor: "rgba(255,255,255,0.02)",
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                }}
              >
                <TrendIcon
                  summary={
                    (result.trend.trend_summary as string) || "stable"
                  }
                />
                <Typography variant="body2">
                  {t("evaluation.trend")}:{" "}
                  {(result.trend.trend_summary as string) || "N/A"}
                </Typography>
                {result.trend.followers_change != null && (
                  <Chip
                    label={`${(result.trend.followers_change as number) >= 0 ? "+" : ""}${(result.trend.followers_change as number).toLocaleString()}`}
                    size="small"
                    sx={{ height: 20, fontSize: "0.7rem" }}
                  />
                )}
              </Box>
            )}

            {/* Tags */}
            {result.tags?.length > 0 && (
              <Stack spacing={1}>
                <Typography variant="subtitle2">{t("common.tags")}</Typography>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {result.tags.map((tag) => (
                    <Chip key={tag} label={tag} size="small" color="secondary" />
                  ))}
                </Stack>
              </Stack>
            )}

            {/* Risks */}
            {result.risks?.length > 0 && (
              <Stack spacing={1}>
                <Typography variant="subtitle2">
                  {t("common.risks")}
                </Typography>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {result.risks.map((risk) => (
                    <Chip key={risk} label={risk} size="small" color="warning" />
                  ))}
                </Stack>
              </Stack>
            )}

            {/* Report */}
            <Stack spacing={1}>
              <Typography variant="subtitle2">{t("common.report")}</Typography>
              <Box
                sx={{
                  borderRadius: 3,
                  p: 2,
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "rgba(255,255,255,0.02)",
                  minHeight: 120,
                  maxHeight: 400,
                  overflowY: "auto",
                }}
              >
                <Typography
                  variant="body2"
                  color="text.secondary"
                  whiteSpace="pre-line"
                  sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}
                >
                  {result.report || t("common.placeholderReport")}
                </Typography>
              </Box>
            </Stack>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}
