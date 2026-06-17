/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#070b14',
          800: '#0b1120',
          700: '#111a2e',
          600: '#1a2540',
        },
        iris: '#7c6cff',
        cyan: '#22d3ee',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glass: '0 8px 32px rgba(8, 12, 24, 0.55)',
        glow: '0 0 0 1px rgba(124, 108, 255, 0.25), 0 12px 40px rgba(34, 211, 238, 0.12)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
