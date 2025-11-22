import {
  AppBar,
  Box,
  IconButton,
  MenuItem,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import { Github } from "lucide-react";
import { useTranslation } from "react-i18next";
import StatusBadge from "./StatusBadge";
import { HealthResponse } from "../api/types";

interface AppHeaderProps {
  health?: HealthResponse;
  isLoading: boolean;
}

export default function AppHeader({ health, isLoading }: AppHeaderProps) {
  const { t, i18n } = useTranslation();

  return (
    <AppBar
      position="static"
      elevation={0}
      sx={{
        mb: 4,
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        background: "linear-gradient(90deg,#111229 0%, #141724 100%)",
      }}
    >
      <Toolbar sx={{ gap: 3 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5" fontWeight={700}>
            {t("app.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("app.subtitle")}
          </Typography>
        </Box>
        <StatusBadge health={health} isLoading={isLoading} />
        <TextField
          select
          label={t("app.language")}
          size="small"
          value={i18n.language}
          onChange={(e) => i18n.changeLanguage(e.target.value)}
          sx={{ minWidth: 120 }}
        >
          <MenuItem value="ko">한국어</MenuItem>
          <MenuItem value="en">English</MenuItem>
        </TextField>
        <IconButton
          color="inherit"
          size="large"
          component="a"
          href="https://github.com/"
          target="_blank"
          rel="noreferrer"
        >
          <Github size={20} />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}

