/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Fondos
        'bg-primary':   '#080C0A',
        'bg-secondary': '#0D1410',
        'bg-surface':   '#121A14',
        'bg-deep':      '#1A2E1E',

        // Verdes
        'green-vivid':  '#4ADE80',
        'green-light':  '#86EFAC',
        'green-muted':  '#A8D5A2',
        'green-neon':   '#00FF88',
        'green-border': 'rgba(168,213,162,0.15)',

        // Texto
        'text-primary':   '#F9FAFB',
        'text-secondary': '#9CA3AF',
        'text-tertiary':  '#4B5563',
      },
      fontFamily: {
        logo:      ['"Space Grotesk"', 'sans-serif'],
        hero:      ['"Cormorant Garamond"', 'serif'],
        display:   ['"Playfair Display"', 'serif'],
        ui:        ['"Inter"', 'sans-serif'],
        mono:      ['"DM Mono"', 'monospace'],
      },
      letterSpacing: {
        logo: '0.18em',
        wide: '0.08em',
      },
      animation: {
        'pulse-ring': 'pulse-ring 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ken-burns':  'ken-burns 14s ease-in-out infinite alternate',
      },
      keyframes: {
        'pulse-ring': {
          '0%':   { transform: 'scale(1)',   opacity: '0.6' },
          '100%': { transform: 'scale(1.55)', opacity: '0' },
        },
        'ken-burns': {
          '0%':   { transform: 'scale(1.0)' },
          '100%': { transform: 'scale(1.08)' },
        },
      },
    },
  },
  plugins: [],
}
