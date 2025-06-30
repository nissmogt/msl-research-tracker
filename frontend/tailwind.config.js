/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Persian-inspired custom colors as primary
        primary: {
          50:  '#F8F8F0',   // ivory (backgrounds)
          100: '#E6FAF8',   // very light turk (custom blend for bg hover)
          200: '#66E5DC',   // turk light (subtle backgrounds)
          300: '#30D5C8',   // turk (main accent, backgrounds)
          400: '#475CCF',   // lajvard light (secondary accent)
          500: '#1C39BB',   // lajvard (main buttons, links)
          600: '#142887',   // lajvard dark (button hover, headings)
          700: '#A23E48',   // clay (danger, warning, or strong accent)
          800: '#D4AF37',   // gold (highlight, badge, or accent)
          900: '#22223B',   // deep blue/black for text (custom for contrast)
        },
        // Named for reference, but use primary palette in components
        turk: {
          DEFAULT: '#30D5C8',
          light: '#66E5DC',
          dark: '#28B1A9',
        },
        lajvard: {
          DEFAULT: '#1C39BB',
          light: '#475CCF',
          dark: '#142887',
        },
        ivory: '#F8F8F0',
        gold: '#D4AF37',
        clay: '#A23E48',
      },
    },
  },
  plugins: [],
} 