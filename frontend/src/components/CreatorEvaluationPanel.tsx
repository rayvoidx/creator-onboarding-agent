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
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { evaluateCreator } from "../api/client";
import {
  CreatorEvaluationPayload,
  CreatorEvaluationResponse,
} from "../api/types";
import EvaluationResultCard from "./EvaluationResultCard";

interface FormValues extends CreatorEvaluationPayload {
  profile_url?: string;
}

const defaultValues: FormValues = {
  platform: "instagram",
  handle: "",
  profile_url: "",
};

export default function CreatorEvaluationPanel() {
  const { t } = useTranslation();
  const {
    control,
    handleSubmit,
    reset,
    formState: { isValid },
  } = useForm<FormValues>({
    defaultValues,
    mode: "onChange",
  });

  const evaluationMutation = useMutation({
    mutationFn: evaluateCreator,
  });

  const onSubmit = (values: FormValues) => {
    evaluationMutation.mutate(values, {
      onSuccess: () => {
        reset(values);
      },
    });
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={5}>
        <Card>
          <CardHeader
            title={t("evaluation.title")}
            subheader={t("evaluation.subtitle")}
          />
          <Divider />
          <CardContent>
            <Stepper
              activeStep={
                evaluationMutation.isSuccess
                  ? 2
                  : evaluationMutation.isPending
                  ? 1
                  : 0
              }
              alternativeLabel
              sx={{ mb: 3 }}
            >
              {[t("evaluation.steps.input"), t("evaluation.steps.analysis"), t("evaluation.steps.review")].map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
            <Stack
              component="form"
              spacing={2.5}
              onSubmit={handleSubmit(onSubmit)}
            >
              <Controller
                control={control}
                name="platform"
                rules={{ required: "플랫폼을 선택하세요." }}
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
                name="handle"
                rules={{ required: "핸들을 입력하세요." }}
                render={({ field, fieldState }) => (
                  <TextField
                    label={`${t("evaluation.handle")} (@username)`}
                    placeholder="@creator_123"
                    error={!!fieldState.error}
                    helperText={fieldState.error?.message}
                    {...field}
                  />
                )}
              />
              <Controller
                control={control}
                name="profile_url"
                render={({ field }) => (
                  <TextField
                    label={`${t("evaluation.profileUrl")} (${t("common.optional")})`}
                    placeholder="https://instagram.com/creator"
                    {...field}
                  />
                )}
              />
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={!isValid || evaluationMutation.isPending}
              >
                {evaluationMutation.isPending
                  ? t("common.evaluating")
                  : t("common.runEvaluation")}
              </Button>
              {evaluationMutation.isError && (
                <Alert severity="error">
                  {(evaluationMutation.error as Error)?.message ??
                    "평가에 실패했습니다."}
                </Alert>
              )}
              <Typography variant="caption" color="text.secondary">
                {t("evaluation.helper")}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={7}>
        <Box height="100%">
          <EvaluationResultCard
            loading={evaluationMutation.isPending}
            result={
              evaluationMutation.data as CreatorEvaluationResponse | undefined
            }
          />
        </Box>
      </Grid>
    </Grid>
  );
}

