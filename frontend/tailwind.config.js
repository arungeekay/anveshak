/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Government-grade navy palette.
        navy: {
          950: "#0a0f1f",
          900: "#0f1830",
          800: "#16233f",
          700: "#1e3a5f",
          600: "#2b4c7e",
        },
        accent: "#3b82f6",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        kannada: ['"Noto Sans Kannada"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
