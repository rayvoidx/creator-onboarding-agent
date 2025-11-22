import {
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { fetchAgentModelStatus } from "../api/client";
import { AgentModelConfig } from "../api/types";

const FEATURED_AGENTS = ["creator", "mission", "analytics", "search", "rag"];

function formatAgentName(name: string): string {
  if (!name) return "";
  return name
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function AgentCard({
  agent,
  config,
}: {
  agent: string;
  config: AgentModelConfig;
}) {
  const { t } = useTranslation();
  const llms = config.llm_models ?? [];

  return (
    <Card
      variant="outlined"
      sx={{
        height: "100%",
        borderColor: "rgba(255,255,255,0.08)",
        background: "rgba(17, 17, 28, 0.6)",
      }}
    >
      <CardHeader
        title={formatAgentName(agent)}
        subheader={t("agentModels.models")}
        sx={{ pb: 0 }}
      />
      <CardContent sx={{ pt: 1 }}>
        <Stack spacing={1.5}>
          <Stack spacing={1}>
            <Typography variant="caption" color="text.secondary">
              {t("agentModels.models")}
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={1}>
              {llms.length > 0 ? (
                llms.map((model) => (
                  <Chip
                    key={model}
                    label={model}
                    variant="outlined"
                    size="small"
                    color="primary"
                  />
                ))
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {t("agentModels.noData")}
                </Typography>
              )}
            </Stack>
          </Stack>

          {config.embedding_model && (
            <Stack spacing={0.5}>
              <Typography variant="caption" color="text.secondary">
                {t("agentModels.embedding")}
              </Typography>
              <Typography variant="body2">{config.embedding_model}</Typography>
            </Stack>
          )}

          {config.vector_db && (
            <Stack spacing={0.5}>
              <Typography variant="caption" color="text.secondary">
                {t("agentModels.vector")}
              </Typography>
              <Typography variant="body2">{config.vector_db}</Typography>
            </Stack>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function AgentModelStatusPanel() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["agent-model-status"],
    queryFn: fetchAgentModelStatus,
    staleTime: 60_000,
  });

  const agentEntries = Object.entries(data?.agent_models ?? {});
  const sortedAgents = agentEntries.sort((a, b) => {
    const aIndex = FEATURED_AGENTS.indexOf(a[0]);
    const bIndex = FEATURED_AGENTS.indexOf(b[0]);
    if (aIndex === -1 && bIndex === -1) {
      return a[0].localeCompare(b[0]);
    }
    if (aIndex === -1) return 1;
    if (bIndex === -1) return -1;
    return aIndex - bIndex;
  });

  const llmStatusEntries = Object.entries(data?.llm_status ?? {});

  return (
    <Card
      sx={{
        mb: 4,
        borderColor: "rgba(255,255,255,0.08)",
        background: "linear-gradient(135deg, rgba(20,20,40,0.9), rgba(25,25,55,0.9))",
      }}
    >
      <CardHeader
        title={t("agentModels.title")}
        subheader={
          data?.timestamp
            ? t("agentModels.lastUpdated", {
                time: dayjs(data.timestamp).format("YYYY-MM-DD HH:mm:ss"),
              })
            : t("agentModels.subtitle")
        }
      />
      <CardContent>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Typography variant="caption" color="text.secondary">
              {t("agentModels.llmFleet")}
            </Typography>
            {llmStatusEntries.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {isLoading
                  ? t("health.checking")
                  : t("agentModels.noData")}
              </Typography>
            )}
            <Stack direction="row" flexWrap="wrap" gap={1}>
              {llmStatusEntries.map(([model, status]) => (
                <Tooltip
                  key={model}
                  title={`${status.provider?.toUpperCase() ?? ""} · ${
                    t("agentModels.priority") ?? ""
                  } ${status.priority ?? "-"}`}
                >
                  <Chip
                    label={`${model} (${status.status})`}
                    size="small"
                    color={
                      status.status === "healthy"
                        ? "success"
                        : status.status === "degraded"
                        ? "warning"
                        : "error"
                    }
                    variant="outlined"
                  />
                </Tooltip>
              ))}
            </Stack>
          </Stack>

          <Divider />

          {isLoading && (
            <Stack direction="row" alignItems="center" gap={1}>
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                {t("health.checking")}
              </Typography>
            </Stack>
          )}

          {isError && (
            <Typography variant="body2" color="error">
              {t("agentModels.noData")}
            </Typography>
          )}

          {!isLoading && !isError && sortedAgents.length > 0 && (
            <Grid container spacing={2}>
              {sortedAgents.map(([agentName, config]) => (
                <Grid key={agentName} item xs={12} md={4}>
                  <AgentCard agent={agentName} config={config} />
                </Grid>
              ))}
            </Grid>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

