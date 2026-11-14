/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      colors: {
        // Cooler, calmer greys; gray-900 becomes the brand navy, so every dark button matches.
        gray: {
          50: '#f6f8fa', 100: '#eef2f5', 200: '#e1e7ec', 300: '#cbd4dc', 400: '#94a3b1',
          500: '#64748b', 600: '#4b5a6a', 700: '#354353', 800: '#1f2d3b', 900: '#0f2436',
        },
        brand: {
          50: '#ecf8f9', 100: '#d3eff1', 200: '#a6dee3', 400: '#3fb5c1', 500: '#1f9aa8',
          600: '#16808d', 700: '#126872', 900: '#0d2233',
        },
      },
      boxShadow: {
        card: '0 1px 2px rgba(15, 36, 54, 0.04), 0 1px 3px rgba(15, 36, 54, 0.06)',
      },
    },
  },
  plugins: [],
};