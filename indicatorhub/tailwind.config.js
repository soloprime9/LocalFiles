/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        trading: {
          bg: "#0A0A0A",
          card: "#111111",
          cardHover: "#161616",
          border: "#1F2937",
          borderHover: "#374151",
          accent: "#F59E0B",
          accentHover: "#D97706",
          blue: "#3B82F6",
          success: "#10B981",
          danger: "#EF4444",
          warning: "#F59E0B",
          textPrimary: "#FFFFFF",
          textSecondary: "#9CA3AF",
          textMuted: "#6B7280",
        },
      },
      fontFamily: {
        inter: ["Inter", "sans-serif"],
      },
      borderRadius: {
        card: "8px",
        btn: "6px",
        input: "4px",
      },
    },
  },
  plugins: [],
};
