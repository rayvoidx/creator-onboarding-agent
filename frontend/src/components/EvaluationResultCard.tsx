import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useTranslation } from "react-i18next";
import { CreatorEvaluationResponse } from "../api/types";
import { Badge } from "./ui/badge";

interface EvaluationResultCardProps {
  loading: boolean;
  result?: CreatorEvaluationResponse;
}

export default function EvaluationResultCard({
  loading,
  result,
}: EvaluationResultCardProps) {
  const { t } = useTranslation();
  const breakdownEntries = result
    ? Object.entries(result.score_breakdown || {})
    : [];
  const chartWidth = result
    ? Math.max(
        320,
        Math.min(640, Math.max(breakdownEntries.length, 1) * 140)
      )
    : 320;

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
                <Typography variant="h2" color="primary.main">
                  {result.grade}
                </Typography>
              </Box>
            </Box>

            <Box>
              <Typography variant="subtitle2">
                {t("common.scoreDetail")}
              </Typography>
              <Box sx={{ overflowX: "auto", px: 1 }}>
                <BarChart
                  dataset={breakdownEntries.map(([label, value]) => ({
                    label,
                    value: typeof value === "number" ? value : Number(value),
                  }))}
                  xAxis={[{ scaleType: "band", dataKey: "label" }]}
                  series={[
                    {
                      dataKey: "value",
                      color: "#8b5cf6",
                    },
                  ]}
                  width={chartWidth}
                  height={220}
                  margin={{ top: 20, bottom: 30, left: 40, right: 20 }}
                />
              </Box>
            </Box>

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

            {result.risks?.length > 0 && (
              <Stack spacing={1}>
                <Typography variant="subtitle2">{t("common.risks")}</Typography>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {result.risks.map((risk) => (
                    <Chip key={risk} label={risk} size="small" color="warning" />
                  ))}
                </Stack>
              </Stack>
            )}

            <Stack spacing={1}>
              <Typography variant="subtitle2">{t("common.report")}</Typography>
              <Box
                sx={{
                  borderRadius: 3,
                  p: 2,
                  border: "1px solid rgba(255,255,255,0.08)",
                  backgroundColor: "rgba(255,255,255,0.02)",
                  minHeight: 120,
                }}
              >
                <Typography
                  variant="body2"
                  color="text.secondary"
                  whiteSpace="pre-line"
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

