/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#0A0E1A",
          card: "#111827",
          surface: "#0F172A",
          border: "#1F2937",
          accent: "#4F46E5",
          accentHover: "#4338CA",
          success: "#10B981",
          warning: "#F59E0B",
          danger: "#EF4444"
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace']
      }
    },
  },
  plugins: [],
}
