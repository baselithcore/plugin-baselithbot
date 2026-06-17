/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // React Flow controls + deep surfaces
        ink: {
          950: '#070a12',
          900: '#0a0e18',
          850: '#0e1320',
          800: '#131a2b',
          700: '#1b2540',
          600: '#243156',
        },
        // Primary brand accent — a confident sky/cyan
        accent: {
          DEFAULT: '#38bdf8',
          soft: '#7dd3fc',
          deep: '#0ea5e9',
          ink: '#0b3a52',
        },
        // Secondary accent for data viz variety
        iris: {
          DEFAULT: '#818cf8',
          soft: '#a5b4fc',
          deep: '#6366f1',
        },
        sev: {
          low: '#34d399',
          medium: '#fbbf24',
          high: '#fb923c',
          critical: '#fb7185',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        xl: '0.875rem',
        '2xl': '1.125rem',
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(56,189,248,0.16), 0 24px 60px -20px rgba(14,165,233,0.45)',
        card: '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 18px 40px -28px rgba(0,0,0,0.9)',
        lift: '0 1px 0 0 rgba(255,255,255,0.06) inset, 0 24px 60px -24px rgba(0,0,0,0.95)',
        focus: '0 0 0 2px rgba(56,189,248,0.45)',
      },
      backgroundImage: {
        sheen: 'linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0) 42%)',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.22s ease-out both',
        shimmer: 'shimmer 1.4s infinite',
      },
    },
  },
  plugins: [],
};
