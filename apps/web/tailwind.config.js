/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        netra: {
          bg: "#05060A",
          surface: "#080912",
          card: "#0B0D14",
          border: "#11131D",
          hover: "#1C1F2B",
          purple: "#8B2CFF",
          deepViolet: "#5B18D6",
          cyan: "#19D9D0",
          text: "#F4F4F7",
          muted: "#A6A8B3",
          subtle: "#666A78",
          valid: "#10B981",
          amber: "#F59E0B",
          red: "#EF4444"
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']
      }
    },
  },
  plugins: [],
}
