import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surfaces — flat near-black, no navy wash
        bg: {
          base: '#08090c',
          elevated: '#0e1015',
          card: '#11141b',
          overlay: '#171a23',
          hover: '#1d2130',
          line: '#252a37',
          'line-strong': '#3a4154',
        },
        // Text
        text: {
          primary: '#e9ecf2',
          secondary: '#a8b0bf',
          muted: '#727a8c',
          subtle: '#4a5263',
          inverse: '#0a0e1c',
        },
        // Brand — single restrained signal color, not neon
        brand: {
          50: '#eef5fb',
          100: '#d2e3f3',
          200: '#a4c5e3',
          300: '#76a7d4',
          400: '#4f8ac1',
          500: '#3a73ad',
          600: '#2c5b8a',
          DEFAULT: '#5b9bd5',
        },
        // Accents — kept as compatibility aliases for existing classnames.
        // Values intentionally aligned to the muted brand to retire neon tells.
        accent: {
          neon: '#5b9bd5',
          violet: '#7a8aa8',
          electric: '#5b9bd5',
          mint: '#6db89e',
          warn: '#d9a200',
          fail: '#c1485e',
          info: '#5d8fb5',
        },
        // Severity (semantic; keep distinct hues but desaturated)
        sev: {
          info: '#5d8fb5',
          low: '#6db89e',
          medium: '#d6a13a',
          high: '#d97a3a',
          critical: '#c1485e',
        },
        // Status
        status: {
          success: '#5fa86b',
          warning: '#d6a13a',
          error: '#c84d4d',
          info: '#5d8fb5',
          idle: '#6e7a96',
        },
      },
      fontFamily: {
        display: ['"JetBrains Mono Variable"', 'JetBrains Mono', 'ui-monospace', 'monospace'],
        body: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono Variable"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        // Glow reserved for active/live indicators only — much softer
        glow: '0 0 0 1px rgba(91, 155, 213, 0.30)',
        'glow-soft': '0 0 0 1px rgba(91, 155, 213, 0.18)',
        'glow-violet': '0 0 0 1px rgba(91, 155, 213, 0.18)',
        card: '0 1px 0 0 rgba(255, 255, 255, 0.02), 0 0 0 1px rgba(37, 42, 55, 0.6)',
        elevated: '0 1px 0 0 rgba(255, 255, 255, 0.02), 0 0 0 1px rgba(37, 42, 55, 0.7)',
        ai: '0 0 0 1px rgba(91, 155, 213, 0.30)',
      },
      backgroundImage: {
        'grid-cyber':
          'linear-gradient(rgba(37, 42, 55, 0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(37, 42, 55, 0.4) 1px, transparent 1px)',
        'gradient-brand':
          'linear-gradient(135deg, rgba(91, 155, 213, 0.10) 0%, rgba(91, 155, 213, 0.02) 100%)',
        'gradient-card':
          'linear-gradient(180deg, rgba(255,255,255,0.01) 0%, rgba(255,255,255,0) 100%)',
        'gradient-ai':
          'linear-gradient(135deg, rgba(91, 155, 213, 0.12) 0%, rgba(91, 155, 213, 0.03) 100%)',
        'gradient-funnel':
          'linear-gradient(90deg, rgba(193,72,94,0.08) 0%, rgba(217,122,58,0.14) 30%, rgba(214,161,58,0.20) 65%, rgba(193,72,94,0.40) 100%)',
      },
      backgroundSize: {
        'grid-24': '24px 24px',
      },
      borderRadius: {
        sm: '0.25rem',
        DEFAULT: '0.375rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '1rem',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'enter-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'enter-fade': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        scanline: 'scanline 2.5s linear infinite',
        'enter-up': 'enter-up 220ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'enter-fade': 'enter-fade 180ms cubic-bezier(0.16, 1, 0.3, 1) both',
      },
      transitionTimingFunction: {
        'out-quart': 'cubic-bezier(0.25, 1, 0.5, 1)',
        'out-quint': 'cubic-bezier(0.22, 1, 0.36, 1)',
        'out-expo': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config;
