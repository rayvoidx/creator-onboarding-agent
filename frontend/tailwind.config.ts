import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0f1014",
        card: "#15171f",
        accent: {
          DEFAULT: "#8b5cf6",
          muted: "#a855f7",
        },
      },
      borderRadius: {
        xl: "1rem",
      },
      fontFamily: {
        sans: [
          '"Pretendard"',
          '"Spoqa Han Sans Neo"',
          '"Inter"',
          "system-ui",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;

