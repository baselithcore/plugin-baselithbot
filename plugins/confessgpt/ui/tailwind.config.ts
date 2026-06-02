import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        void: '#0a0712',
        nave: '#14101e',
        apse: '#1d1730',
        'apse-glow': '#2a1f44',
        gold: {
          DEFAULT: '#c9a86a',
          bright: '#e8c98a',
          deep: '#8c7340',
        },
        parchment: {
          DEFAULT: '#f4ead3',
          soft: '#d9cfb8',
        },
        ash: '#7a7185',
        crimson: {
          DEFAULT: '#8b1a2a',
          glow: '#c44056',
        },
        emerald: '#4a7d5a',
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', '"EB Garamond"', 'Georgia', 'serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        liturgic: '0.24em',
      },
      borderColor: {
        'gold-subtle': 'rgba(201, 168, 106, 0.12)',
        'gold-medium': 'rgba(201, 168, 106, 0.28)',
        'gold-strong': 'rgba(201, 168, 106, 0.55)',
      },
      backgroundColor: {
        'surface-1': 'rgba(255, 255, 255, 0.025)',
        'surface-2': 'rgba(255, 255, 255, 0.045)',
        'surface-3': 'rgba(255, 255, 255, 0.07)',
      },
      boxShadow: {
        'glow-gold': '0 0 32px rgba(201, 168, 106, 0.25)',
        'glow-gold-strong': '0 0 48px rgba(232, 201, 138, 0.45)',
        'glow-crimson': '0 0 24px rgba(196, 64, 86, 0.4)',
        deep: '0 30px 80px -20px rgba(0, 0, 0, 0.75)',
      },
      animation: {
        flicker: 'flicker 2.8s cubic-bezier(0.65, 0, 0.35, 1) infinite',
        breathe: 'breathe 2.4s cubic-bezier(0.65, 0, 0.35, 1) infinite',
        pulse: 'pulse 3.2s cubic-bezier(0.65, 0, 0.35, 1) infinite',
        'mic-pulse': 'mic-pulse 1.4s cubic-bezier(0.65, 0, 0.35, 1) infinite',
      },
      keyframes: {
        flicker: {
          '0%, 100%': {
            boxShadow: '0 0 16px rgba(201,168,106,0.8), 0 0 4px rgba(232,201,138,0.9)',
          },
          '50%': {
            boxShadow: '0 0 24px rgba(232,201,138,1), 0 0 8px rgba(232,201,138,1)',
          },
        },
        breathe: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.04)' },
        },
        pulse: {
          '0%, 100%': { opacity: '0.55', transform: 'scale(0.85)' },
          '50%': { opacity: '1', transform: 'scale(1)' },
        },
        'mic-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(196,64,86,0.6)' },
          '50%': { boxShadow: '0 0 0 14px rgba(196,64,86,0)' },
        },
      },
    },
  },
  plugins: [],
};

export default config;
