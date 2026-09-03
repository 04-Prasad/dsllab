/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        midnight: {
          canvas: "#05060f",
          steel: "#2f343e",
          gridline: "#3f4959",
        },
        frost: {
          highlight: "#d8ecf8",
          glow: "#d1e4fa",
          mist: "#c7d3ea",
          veil: "#9da7ba",
          fill: "rgba(199, 211, 234, 0.12)",
          glass: "rgba(186, 214, 247, 0.03)",
          edge: "rgba(186, 215, 247, 0.12)",
        },
        violet: {
          void: "#663af3",
        },
        blueprint: "#b6d9fc",
        dark: {
          bg: "#05060f",
          card: "#0d101d",
          border: "rgba(186, 215, 247, 0.12)",
          hover: "rgba(186, 214, 247, 0.06)",
        },
        risk: {
          low: "#10B981",
          medium: "#F59E0B",
          high: "#EF4444",
          critical: "#DC2626",
        },
      },
      borderRadius: {
        cards: "16px",
        badges: "6px",
        inputs: "6px",
        modals: "16px",
        buttons: "999px",
        iconcontainers: "9999px",
      },
      boxShadow: {
        sm: "rgba(186, 207, 247, 0.32) 0px 0px 6px 0px",
        md: "rgba(238, 186, 247, 0.24) 0px 0px 12px 0px",
        glass: "inset 0 1px 1px rgba(216, 236, 248, 0.2), inset 0 24px 48px rgba(168, 216, 245, 0.06), 0 16px 32px rgba(0, 0, 0, 0.3)",
        card: "inset 0 1px 1px rgba(199, 211, 234, 0.12), inset 0 24px 48px rgba(199, 211, 234, 0.05), 0 24px 32px rgba(6, 6, 14, 0.7)",
        glow: "0 0 12px rgba(102, 58, 243, 0.35)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
}
