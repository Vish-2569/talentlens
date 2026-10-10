import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FBFAF7",
        surface: "#FFFFFF",
        ink: "#1B1F2A",
        muted: "#5B6170",
        hairline: "#E4E1DA",
        accent: "#1F3A5F",
        redline: "#B42318",
        amber: "#B54708",
        green: "#067647",
      },
      fontFamily: {
        serif: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "figure-lg": ["2.25rem", { lineHeight: "1", fontWeight: "500" }],
        "figure-md": ["1.5rem", { lineHeight: "1.1", fontWeight: "500" }],
      },
      borderRadius: {
        DEFAULT: "4px",
        md: "6px",
      },
      boxShadow: {
        none: "none",
      },
      ringWidth: {
        DEFAULT: "2px",
      },
      ringColor: {
        DEFAULT: "#1F3A5F",
      },
      transitionDuration: {
        DEFAULT: "150ms",
        slow: "200ms",
      },
    },
    fontFamily: {
      serif: ['"Source Serif 4"', "Georgia", "serif"],
      sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
      mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
    },
  },
  plugins: [],
} satisfies Config;
