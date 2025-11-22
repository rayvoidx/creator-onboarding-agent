import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { LineChart } from "@mui/x-charts/LineChart";
import { createAnalyticsReport } from "../api/client";
import { AnalyticsRequestPayload, AnalyticsResponse } from "../api/types";

const defaultValues: AnalyticsRequestPayload = {
  user_id: "user_analytics",
  session_id: `session_${Date.now()}`,
  report_type: "learning_progress",
};

export default function AnalyticsPanel() {
  const { t } = useTranslation();
  const {
    control,
    handleSubmit,
    formState: { isValid },
  } = useForm<AnalyticsRequestPayload>({
    defaultValues,
    mode: "onChange",
  });

  const analyticsMutation = useMutation({
    mutationFn: createAnalyticsReport,
  });

  const onSubmit = (values: AnalyticsRequestPayload) => {
    analyticsMutation.mutate(values);
  };

  return (
    <Card>
      <CardHeader
        title={t("analytics.title")}
        subheader={t("analytics.subtitle")}
      />
      <Divider />
      <CardContent>
        <Stack
          spacing={3}
          component="form"
          maxWidth={600}
          onSubmit={handleSubmit(onSubmit)}
        >
          <Controller
            control={control}
            name="report_type"
            render={({ field }) => (
              <TextField select label={t("analytics.type")} {...field}>
                <MenuItem value="learning_progress">
                  {t("app.nav.evaluation")}
                </MenuItem>
                <MenuItem value="engagement">Engagement</MenuItem>
                <MenuItem value="performance">Performance</MenuItem>
                <MenuItem value="creator_mission_performance">
                  Creator vs Mission
                </MenuItem>
                <MenuItem value="reward_efficiency">Reward Efficiency</MenuItem>
              </TextField>
            )}
          />
          <Controller
            control={control}
            name="user_id"
            rules={{ required: "사용자 ID는 필수입니다." }}
            render={({ field, fieldState }) => (
              <TextField
                label={t("analytics.user")}
                error={!!fieldState.error}
                helperText={fieldState.error?.message}
                {...field}
              />
            )}
          />

          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || analyticsMutation.isPending}
          >
            {analyticsMutation.isPending
              ? t("common.generatingReport")
              : t("common.createReport")}
          </Button>
          {analyticsMutation.isError && (
            <Alert severity="error">
              {(analyticsMutation.error as Error)?.message ??
                "리포트 생성에 실패했습니다."}
            </Alert>
          )}
        </Stack>

        <Box mt={4}>
          <ReportPreview
            loading={analyticsMutation.isPending}
            data={analyticsMutation.data}
          />
        </Box>
      </CardContent>
    </Card>
  );
}

function ReportPreview({
  data,
  loading,
}: {
  data?: AnalyticsResponse;
  loading: boolean;
}) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("common.generatingReport")}
      </Typography>
    );
  }

  if (!data) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("analytics.placeholder")}
      </Typography>
    );
  }

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1">
        {data.report_type} · {new Date(data.timestamp).toLocaleString()}
      </Typography>
      <Divider />
      <Typography variant="subtitle2">{t("analytics.metrics")}</Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 2,
        }}
      >
        {Object.entries(data.report_data || {}).map(([key, value]) => (
          <Box
            key={key}
            sx={{
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(255,255,255,0.08)",
              backgroundColor: "rgba(255,255,255,0.02)",
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {key}
            </Typography>
            <Typography variant="h6">
              {typeof value === "number" ? value.toFixed(2) : String(value)}
            </Typography>
          </Box>
        ))}
      </Box>

      {Object.entries(data.report_data || {}).some(
        ([, value]) => typeof value === "number"
      ) && (
        <Box sx={{ borderRadius: 3, border: "1px solid rgba(255,255,255,0.08)", p: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
            {t("analytics.metrics")}
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <LineChart
              dataset={Object.entries(data.report_data || {})
                .filter(([, value]) => typeof value === "number")
                .map(([label, value], idx) => ({
                  point: idx + 1,
                  label,
                  value: Number(value),
                }))}
              xAxis={[{ dataKey: "point", valueFormatter: (v) => `#${v}` }]}
              series={[{ dataKey: "value", color: "#34d399" }]}
              width={Math.max(
                320,
                Math.min(
                  640,
                  Object.entries(data.report_data || {}).filter(
                    ([, value]) => typeof value === "number"
                  ).length * 160
                )
              )}
              height={220}
              margin={{ top: 20, bottom: 30, left: 40, right: 20 }}
            />
          </Box>
        </Box>
      )}

      {data.insights?.length > 0 && (
        <>
          <Typography variant="subtitle2">{t("analytics.insights")}</Typography>
          <ul>
            {data.insights.map((insight) => (
              <li key={insight}>
                <Typography variant="body2">{insight}</Typography>
              </li>
            ))}
          </ul>
        </>
      )}
    </Stack>
  );
}

