import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#101828",
        mist: "#f6f8f4",
        fern: "#2f6b4f",
        moss: "#8bae78",
        clay: "#c96f4a",
        line: "#d6ddcf",
      },
      boxShadow: {
        panel: "0 18px 40px rgba(16, 24, 40, 0.08)",
      },
      fontFamily: {
        sans: ["Avenir Next", "Segoe UI", "Helvetica Neue", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
