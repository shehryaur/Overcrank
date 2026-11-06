/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        chassis: "#07080C",
        panel: "#0E1017",
        rail: "#1E2330",
        phosphor: "#10B981",
        amberSignal: "#F59E0B",
        hazard: "#EF4444",
        cyanMark: "#22D3EE",
      },
      fontFamily: {
        display: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      keyframes: {
        pulseLed: {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 0 0 rgba(16,185,129,0.6)" },
          "50%": { opacity: "0.55", boxShadow: "0 0 12px 2px rgba(16,185,129,0.45)" },
        },
        sweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(220%)" },
        },
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseLed: "pulseLed 1.6s ease-in-out infinite",
        sweep: "sweep 2.4s linear infinite",
        riseIn: "riseIn 0.45s ease-out both",
      },
    },
  },
  plugins: [],
};
