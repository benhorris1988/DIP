/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bifrost: {
          blue: "#2563eb",
          purple: "#7c3aed",
          pink: "#ec4899",
          amber: "#f59e0b",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backgroundImage: {
        "bifrost-gradient":
          "linear-gradient(135deg, #2563eb 0%, #7c3aed 35%, #ec4899 65%, #f59e0b 100%)",
      },
    },
  },
  plugins: [],
};
