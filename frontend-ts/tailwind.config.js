/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0c0e12',
        surface: '#111318',
        'surface-high': '#23262c',
        primary: '#a0ffc3',
        'primary-container': '#00fc9b',
        'primary-neon': '#00FF9D',
        'on-surface': '#f6f6fc',
        'on-surface-variant': '#aaabb0',
        error: '#ff716c',
        'error-dim': '#d7383b',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
