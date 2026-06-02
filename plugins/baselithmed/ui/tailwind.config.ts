import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Surfaces — warm off-white in light, deep slate in dark.
        surface: {
          base: '#F6F4EE',
          raised: '#FFFFFF',
          sunken: '#EFEBE2',
          dark: {
            base: '#0B1014',
            raised: '#11171D',
            sunken: '#070A0D',
          },
        },
        // Text/structural neutrals tuned for medical reading contrast.
        ink: {
          50: '#F4F6F8',
          100: '#E6EAEE',
          200: '#CFD6DD',
          300: '#A8B2BC',
          400: '#7B8693',
          500: '#586472',
          600: '#3D4954',
          700: '#293440',
          800: '#172029',
          900: '#0B1014',
        },
        // Accent — clinical teal, single primary.
        accent: {
          50: '#E7F4F1',
          100: '#C9E6DF',
          200: '#9DD2C6',
          400: '#3FA28E',
          500: '#1E8A75',
          600: '#0F766E',
          700: '#0A5F58',
          800: '#084842',
        },
        // Italian PS triage scale — semantic, never decorative.
        triage: {
          red: {
            DEFAULT: '#C9252D',
            soft: '#FBE7E7',
            ink: '#5A1014',
          },
          yellow: {
            DEFAULT: '#D89A1B',
            soft: '#FBF3DD',
            ink: '#5E3D02',
          },
          green: {
            DEFAULT: '#1E8A5E',
            soft: '#DDF1E7',
            ink: '#0B3D2A',
          },
          white: {
            DEFAULT: '#9AA4AD',
            soft: '#EEF1F4',
            ink: '#293440',
          },
        },
      },
      fontFamily: {
        sans: [
          'Inter var',
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'sans-serif',
        ],
        display: ['InterDisplay', 'Inter Display', 'Inter var', 'ui-sans-serif', 'system-ui'],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Consolas',
          'monospace',
        ],
      },
      fontSize: {
        // 4pt typographic scale.
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }],
        xs: ['0.75rem', { lineHeight: '1.1rem', letterSpacing: '0.005em' }],
        sm: ['0.8125rem', { lineHeight: '1.25rem' }],
        base: ['0.9375rem', { lineHeight: '1.5rem' }],
        display: [
          '1.625rem',
          { lineHeight: '1.9rem', letterSpacing: '-0.018em', fontWeight: '600' },
        ],
        hero: ['2.5rem', { lineHeight: '2.75rem', letterSpacing: '-0.022em', fontWeight: '600' }],
      },
      borderRadius: {
        sm: '0.375rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '0.9375rem',
        '2xl': '1.25rem',
        '3xl': '1.75rem',
      },
      boxShadow: {
        // Refined elevation system (light + dark friendly).
        e1: '0 1px 0 rgba(11,16,20,0.04), 0 1px 2px rgba(11,16,20,0.06)',
        e2: '0 1px 0 rgba(11,16,20,0.05), 0 6px 14px -8px rgba(11,16,20,0.16)',
        e3: '0 1px 0 rgba(11,16,20,0.06), 0 18px 32px -14px rgba(11,16,20,0.22)',
        focus: '0 0 0 4px rgba(15,118,110,0.18)',
        'inner-soft': 'inset 0 1px 0 rgba(255,255,255,0.5)',
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', transform: 'translateY(-4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-red': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(201,37,45,0.45)' },
          '50%': { boxShadow: '0 0 0 12px rgba(201,37,45,0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-180% 0' },
          '100%': { backgroundPosition: '180% 0' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 220ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-down': 'slide-down 200ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'pulse-red': 'pulse-red 1.8s ease-out infinite',
        shimmer: 'shimmer 1.4s linear infinite',
      },
      backgroundImage: {
        'grid-soft': 'radial-gradient(circle at 1px 1px, rgba(41,52,64,0.07) 1px, transparent 0)',
        'hero-glow':
          'radial-gradient(60% 60% at 50% 0%, rgba(15,118,110,0.10) 0%, transparent 70%)',
      },
      backgroundSize: {
        'grid-sm': '22px 22px',
      },
    },
  },
  plugins: [],
};

export default config;
