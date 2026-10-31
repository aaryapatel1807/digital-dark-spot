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
        ink: "#1d1a16",
        inksoft: "#5c564c",
        paper: "#faf8f3",
        cream: "#f3efe6",
        card: "#ffffff",
        line: "#e6dfd1",
        indigoaccent: "#4338ca",
        indigohover: "#3730a3",
        indigosoft: "#eef0fb",
        sourced: "#2e7d4f",
        suggested: "#b7791f",
        unknown: "#6b7280",
        coral: "#d96c4f",
        gold: "#c9a227",
        teal: "#2a7f7f",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "'Times New Roman'", "serif"],
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(29, 26, 22, 0.05), 0 4px 16px rgba(29, 26, 22, 0.04)",
        lift: "0 2px 4px rgba(29, 26, 22, 0.06), 0 10px 28px rgba(29, 26, 22, 0.08)",
      },
    },
  },
  plugins: [],
};
