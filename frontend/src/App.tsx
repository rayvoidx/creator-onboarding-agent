import { Box, Container, Tab, Tabs } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import AppHeader from "./components/AppHeader";
import CreatorEvaluationPanel from "./components/CreatorEvaluationPanel";
import MissionRecommendationPanel from "./components/MissionRecommendationPanel";
import AnalyticsPanel from "./components/AnalyticsPanel";
import { useHealthCheck } from "./hooks/useHealthCheck";

export default function App() {
  const { data: health, isLoading } = useHealthCheck();
  const { t } = useTranslation();
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <AppHeader health={health} isLoading={isLoading} />
      <Container maxWidth="lg" sx={{ pb: 6 }}>
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          sx={{ mb: 3 }}
        >
          <Tab label={t("app.nav.evaluation")} />
          <Tab label={t("app.nav.mission")} />
          <Tab label={t("app.nav.analytics")} />
        </Tabs>

        {tab === 0 && <CreatorEvaluationPanel />}
        {tab === 1 && <MissionRecommendationPanel />}
        {tab === 2 && <AnalyticsPanel />}
      </Container>
    </Box>
  );
}

