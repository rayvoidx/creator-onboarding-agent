import { Chip, CircularProgress } from "@mui/material";
import { useTranslation } from "react-i18next";
import { HealthResponse } from "../api/types";

interface StatusBadgeProps {
  health?: HealthResponse;
  isLoading: boolean;
}

export default function StatusBadge({ health, isLoading }: StatusBadgeProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return <CircularProgress size={24} color="inherit" />;
  }

  if (!health) {
    return (
      <Chip
        label={t("health.offline")}
        color="error"
        variant="outlined"
        sx={{ borderRadius: 999 }}
      />
    );
  }

  const color = health.status === "healthy" ? "success" : "warning";
  const label =
    health.status === "healthy"
      ? t("health.online", { version: health.version })
      : t("health.warning");

  return (
    <Chip
      label={label}
      color={color}
      variant="outlined"
      sx={{ borderRadius: 999 }}
    />
  );
}

