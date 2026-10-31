/** GapLens design tokens: ink-on-paper, with the three-colour evidence
 *  language (sourced green / suggested amber / unknown grey) as meaning,
 *  not decoration. Every screen uses these tokens, nothing ad hoc. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a18",
        paper: "#faf7f0",
        card: "#ffffff",
        sourced: "#2e7d4f",
        suggested: "#b7791f",
        unknown: "#6b7280",
        coral: "#d96c4f",
        gold: "#c9a227",
        teal: "#2a7f7f",
      },
      fontFamily: {
        display: ["Georgia", "'Times New Roman'", "serif"],
        sans: ["system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
