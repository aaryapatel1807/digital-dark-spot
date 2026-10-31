/** GapLens dashboard tokens: warm paper, deep ink, one restrained
 *  indigo accent, thin borders, quiet shadows. The evidence language
 *  (sourced green / suggested amber / unknown grey) carries meaning,
 *  not decoration. Every screen uses these tokens, nothing ad hoc. */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--ink) / <alpha-value>)",
        inksoft: "rgb(var(--muted) / <alpha-value>)",
        paper: "rgb(var(--paper) / <alpha-value>)",
        cream: "rgb(var(--soft) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        indigoaccent: "rgb(var(--accent) / <alpha-value>)",
        indigohover: "#3730a3",
        indigosoft: "rgb(var(--soft) / <alpha-value>)",
        sourced: "rgb(var(--green) / <alpha-value>)",
        suggested: "rgb(var(--amber) / <alpha-value>)",
        unknown: "rgb(var(--muted) / <alpha-value>)",
        coral: "rgb(var(--red) / <alpha-value>)",
        gold: "#c9a227",
        teal: "#2a7f7f",
      },
      fontFamily: {
        display: ["'Segoe UI'", "system-ui", "sans-serif"],
        sans: ["'Segoe UI'", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(29, 26, 22, 0.05), 0 4px 16px rgba(29, 26, 22, 0.04)",
        lift: "0 2px 4px rgba(29, 26, 22, 0.06), 0 10px 28px rgba(29, 26, 22, 0.08)",
      },
    },
  },
  plugins: [],
};
