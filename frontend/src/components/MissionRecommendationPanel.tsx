import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { LineChart } from "@mui/x-charts/LineChart";
import Editor from "@monaco-editor/react";
import { Download } from "lucide-react";
import { recommendMissions } from "../api/client";
import {
  MissionRecommendPayload,
  MissionRecommendationItem,
} from "../api/types";
import { sampleMissions } from "../data/sampleMissions";
import ShadcnSlider from "./ShadcnSlider";

interface MissionFormValues {
  creator_id: string;
  handle: string;
  platform: string;
  grade: string;
  followers: number;
  engagement_rate: number;
  category: string;
  missions_json: string;
}

const defaultMissionForm: MissionFormValues = {
  creator_id: "creator_acme",
  handle: "@acme_creator",
  platform: "instagram",
  grade: "A",
  followers: 52000,
  engagement_rate: 4.1,
  category: "beauty",
  missions_json: JSON.stringify(sampleMissions, null, 2),
};

export default function MissionRecommendationPanel() {
  const { t } = useTranslation();
  const [minScore, setMinScore] = useState([60]);
  const [exportUrl, setExportUrl] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { isValid },
  } = useForm<MissionFormValues>({
    defaultValues: defaultMissionForm,
    mode: "onChange",
  });

  const missionJson = watch("missions_json");
  const { missions: parsedMissions, error: missionParseError } = useMemo(() => {
    try {
      const parsed = JSON.parse(missionJson || "[]");
      return {
        missions: Array.isArray(parsed) ? parsed : [],
        error: null,
      };
    } catch (err) {
      return {
        missions: [],
        error: (err as Error).message,
      };
    }
  }, [missionJson]);

  const recommendMutation = useMutation({
    mutationFn: recommendMissions,
  });

  useEffect(() => {
    return () => {
      if (exportUrl) {
        URL.revokeObjectURL(exportUrl);
      }
    };
  }, [exportUrl]);

  const onSubmit = (values: MissionFormValues) => {
    const payload: MissionRecommendPayload = {
      creator_id: values.creator_id,
      creator_profile: {
        creator_id: values.creator_id,
        handle: values.handle,
        platform: values.platform,
        followers: values.followers,
        engagement_rate: values.engagement_rate / 100,
        category: values.category,
        completed_missions: 5,
        avg_quality_score: 82,
        current_active_missions: 1,
      },
      onboarding_result: {
        grade: values.grade,
        tags: [values.category],
        risks: [],
      },
      missions: parsedMissions,
      filters: {
        min_score: minScore[0],
      },
    };
    recommendMutation.mutate(payload);
  };

  const exportRecommendations = () => {
    const recommendations = recommendMutation.data?.recommendations ?? [];
    if (!recommendations.length) return;
    const header = [
      "mission_id",
      "mission_name",
      "mission_type",
      "reward_type",
      "score",
      "reasons",
    ];
    const rows = recommendations.map((rec) => [
      rec.mission_id,
      rec.mission_name,
      rec.mission_type,
      rec.reward_type,
      rec.score.toFixed(2),
      rec.reasons.join(" | "),
    ]);
    const csvContent = [header, ...rows]
      .map((row) =>
        row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",")
      )
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    if (exportUrl) {
      URL.revokeObjectURL(exportUrl);
    }
    const url = URL.createObjectURL(blob);
    setExportUrl(url);
    const link = document.createElement("a");
    link.href = url;
    link.download = `missions_${Date.now()}.csv`;
    link.click();
  };

  return (
    <Card>
      <CardHeader
            title={t("mission.title")}
            subheader={t("mission.subtitle")}
      />
      <Divider />
      <CardContent>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Stack
              spacing={2.5}
              component="form"
              onSubmit={handleSubmit(onSubmit)}
            >
              <Controller
                control={control}
                name="creator_id"
                rules={{ required: "크리에이터 ID를 입력하세요." }}
                render={({ field, fieldState }) => (
                  <TextField
                    label={t("mission.creatorId")}
                    error={!!fieldState.error}
                    helperText={fieldState.error?.message}
                    {...field}
                  />
                )}
              />
              <Controller
                control={control}
                name="handle"
                rules={{ required: "핸들을 입력하세요." }}
                render={({ field, fieldState }) => (
                  <TextField
                    label={t("evaluation.handle")}
                    placeholder="@creator"
                    error={!!fieldState.error}
                    helperText={fieldState.error?.message}
                    {...field}
                  />
                )}
              />
              <Controller
                control={control}
                name="platform"
                render={({ field }) => (
                  <TextField select label={t("evaluation.platform")} {...field}>
                    <MenuItem value="instagram">Instagram</MenuItem>
                    <MenuItem value="tiktok">TikTok</MenuItem>
                    <MenuItem value="youtube">YouTube</MenuItem>
                  </TextField>
                )}
              />
              <Controller
                control={control}
                name="grade"
                render={({ field }) => (
                  <TextField select label={t("evaluation.grade")} {...field}>
                    <MenuItem value="S">S</MenuItem>
                    <MenuItem value="A">A</MenuItem>
                    <MenuItem value="B">B</MenuItem>
                    <MenuItem value="C">C</MenuItem>
                  </TextField>
                )}
              />
              <Controller
                control={control}
                name="followers"
                rules={{ min: { value: 0, message: "0 이상 입력" } }}
                render={({ field }) => (
                  <TextField type="number" label={t("mission.followers")} {...field} />
                )}
              />
              <Controller
                control={control}
                name="engagement_rate"
                render={({ field }) => (
                  <TextField
                    type="number"
                    label={t("mission.engagement")}
                    inputProps={{ step: 0.1 }}
                    {...field}
                  />
                )}
              />
              <Controller
                control={control}
                name="category"
                render={({ field }) => (
                  <TextField select label={t("mission.category")} {...field}>
                    <MenuItem value="beauty">뷰티</MenuItem>
                    <MenuItem value="fashion">패션</MenuItem>
                    <MenuItem value="food">푸드</MenuItem>
                    <MenuItem value="tech">테크</MenuItem>
                    <MenuItem value="travel">여행</MenuItem>
                    <MenuItem value="lifestyle">라이프스타일</MenuItem>
                  </TextField>
                )}
              />
              <ShadcnSlider
                label={t("mission.minScore")}
                value={minScore}
                min={30}
                max={95}
                step={5}
                onValueChange={setMinScore}
              />
              <Button
                type="submit"
                variant="contained"
                disabled={
                  !isValid ||
                  recommendMutation.isPending ||
                  !!missionParseError ||
                  !parsedMissions.length
                }
              >
                {recommendMutation.isPending
                  ? t("common.recommending")
                  : t("common.runRecommendation")}
              </Button>
              {(missionParseError || !parsedMissions.length) && (
                <Alert severity="warning">
                  {missionParseError
                    ? t("mission.jsonError", { message: missionParseError })
                    : t("mission.jsonRequired")}
                </Alert>
              )}
            </Stack>
          </Grid>
          <Grid item xs={12} md={8}>
            <Stack spacing={2}>
              <Box
                sx={{
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <Editor
                  height="260px"
                  defaultLanguage="json"
                  theme="vs-dark"
                  value={missionJson}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    scrollBeyondLastLine: false,
                  }}
                  onChange={(value) =>
                    setValue("missions_json", value ?? "", {
                      shouldDirty: true,
                    })
                  }
                />
              </Box>
              <Typography variant="caption" color="text.secondary">
                {t("mission.jsonHelper")}
              </Typography>
              <MissionScoreChart
                data={recommendMutation.data?.recommendations ?? []}
              />
              <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
                <Button
                  startIcon={<Download size={16} />}
                  variant="outlined"
                  size="small"
                  disabled={
                    !(recommendMutation.data?.recommendations?.length ?? 0)
                  }
                  onClick={exportRecommendations}
                >
                  {t("mission.exportCsv")}
                </Button>
              </Box>
              <RecommendationTable
                loading={recommendMutation.isPending}
                data={recommendMutation.data?.recommendations ?? []}
              />
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

function RecommendationTable({
  data,
  loading,
}: {
  data: MissionRecommendationItem[];
  loading: boolean;
}) {
  const { t } = useTranslation();
  const columns: ColumnsType<MissionRecommendationItem> = [
    {
      title: t("mission.columns.mission"),
      dataIndex: "mission_name",
      key: "name",
      render: (value: string, row: MissionRecommendationItem) => (
        <Stack>
          <Typography variant="subtitle2">{value}</Typography>
          <Typography variant="caption" color="text.secondary">
            #{row.mission_id}
          </Typography>
        </Stack>
      ),
    },
    {
      title: t("mission.columns.type"),
      dataIndex: "mission_type",
      key: "type",
      render: (value: string) => value || "-",
    },
    {
      title: t("mission.columns.reward"),
      dataIndex: "reward_type",
      key: "reward_type",
      render: (value: string) => value.toUpperCase(),
    },
    {
      title: t("mission.columns.score"),
      dataIndex: "score",
      key: "score",
      sorter: (a: MissionRecommendationItem, b: MissionRecommendationItem) =>
        a.score - b.score,
      render: (value: number) => `${value.toFixed(1)}점`,
    },
    {
      title: t("mission.columns.reasons"),
      dataIndex: "reasons",
      key: "reasons",
      render: (reasons: string[]) =>
        reasons?.length ? (
          <ul style={{ paddingLeft: 16, margin: 0 }}>
            {reasons.slice(0, 3).map((reason) => (
              <li key={reason}>
                <Typography variant="body2">{reason}</Typography>
              </li>
            ))}
          </ul>
        ) : (
          "-"
        ),
    },
  ];

  return (
    <Box
      sx={{
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
        overflow: "hidden",
        backgroundColor: "rgba(255,255,255,0.02)",
      }}
    >
      <Typography
        variant="subtitle1"
        sx={{ px: 3, pt: 3, pb: 1, fontWeight: 600 }}
      >
        {t("mission.tableTitle")}
      </Typography>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="mission_id"
        loading={loading}
        pagination={{ pageSize: 5 }}
        locale={{ emptyText: t("mission.empty") }}
      />
    </Box>
  );
}

function MissionScoreChart({ data }: { data: MissionRecommendationItem[] }) {
  const { t } = useTranslation();
  const dataset = data.slice(0, 5).map((item, idx) => ({
    rank: idx + 1,
    score: item.score,
    label: item.mission_name,
  }));

  if (!dataset.length) {
    return null;
  }

  const width = Math.max(320, Math.min(640, dataset.length * 160));

  return (
    <Box
      sx={{
        borderRadius: 3,
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "rgba(255,255,255,0.02)",
        p: 2,
        mb: 2,
      }}
    >
      <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
        {t("mission.scoreChart")}
      </Typography>
      <Box sx={{ overflowX: "auto" }}>
        <LineChart
          width={width}
          height={220}
          dataset={dataset}
          xAxis={[{ dataKey: "rank", label: "#", valueFormatter: (v) => `#${v}` }]}
          series={[
            {
              dataKey: "score",
              color: "#f472b6",
            },
          ]}
          margin={{ top: 20, bottom: 30, left: 40, right: 20 }}
        />
      </Box>
    </Box>
  );
}

