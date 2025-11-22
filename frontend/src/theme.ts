import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#8b5cf6",
    },
    secondary: {
      main: "#f472b6",
    },
    background: {
      default: "#0f1014",
      paper: "#15171f",
    },
  },
  shape: {
    borderRadius: 14,
  },
  typography: {
    fontFamily:
      '"Pretendard", "Spoqa Han Sans Neo", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h4: {
      fontWeight: 700,
    },
    h5: {
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(255,255,255,0.06)",
          backgroundImage: "none",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 600,
        },
      },
    },
  },
});

export default theme;

