import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

function rgb(varName: string) {
  return `rgb(var(${varName}) / <alpha-value>)`;
}

const config: Config = {
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          canvas: rgb('--bg-canvas'),
          panel: rgb('--bg-panel'),
          'panel-elev': rgb('--bg-panel-elev'),
          'panel-soft': rgb('--bg-panel-soft'),
        },
        border: {
          DEFAULT: rgb('--border'),
          strong: rgb('--border-strong'),
          subtle: rgb('--border-subtle'),
        },
        text: {
          primary: rgb('--text-primary'),
          secondary: rgb('--text-secondary'),
          muted: rgb('--text-muted'),
          faint: rgb('--text-faint'),
        },
        status: {
          success: rgb('--status-success'),
          warning: rgb('--status-warning'),
          danger: rgb('--status-danger'),
          info: rgb('--status-info'),
        },
        accent: {
          cyan: rgb('--accent-cyan'),
          violet: rgb('--accent-violet'),
          steel: rgb('--accent-steel'),
          sky: rgb('--accent-sky'),
          teal: rgb('--accent-teal'),
        },
      },
      boxShadow: {
        panel: 'var(--shadow-panel)',
        popover: 'var(--shadow-popover)',
        glow: '0 0 0 1px rgb(var(--status-info) / 0.24)',
        'glow-success': '0 0 0 1px rgb(var(--status-success) / 0.22)',
        'glow-danger': '0 0 0 1px rgb(var(--status-danger) / 0.22)',
        'inner-soft': 'var(--shadow-inner-soft)',
        'glass-edge': 'var(--shadow-inner-soft)',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['var(--font-inter)', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '10px',
        '2xl': '12px',
        pill: '9999px',
      },
      transitionTimingFunction: {
        smooth: 'cubic-bezier(0.22, 1, 0.36, 1)',
        snap: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.6' },
          '50%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        glow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(14,165,233,0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(14,165,233,0)' },
        },
        'mesh-spin': {
          '0%': { transform: 'rotate(0deg) scale(1)' },
          '50%': { transform: 'rotate(180deg) scale(1.1)' },
          '100%': { transform: 'rotate(360deg) scale(1)' },
        },
        'evidence-pulse': {
          '0%': { transform: 'scale(1)', filter: 'brightness(1.4)' },
          '40%': { transform: 'scale(1.04)', filter: 'brightness(1.1)' },
          '100%': { transform: 'scale(1)', filter: 'brightness(1)' },
        },
        'dialog-in': {
          '0%': {
            opacity: '0',
            transform: 'translate(-50%, calc(-50% + 8px)) scale(0.98)',
          },
          '100%': {
            opacity: '1',
            transform: 'translate(-50%, -50%) scale(1)',
          },
        },
      },
      animation: {
        shimmer: 'shimmer 2.6s linear infinite',
        'pulse-soft': 'pulse-soft 3s ease-in-out infinite',
        'slide-up': 'slide-up 0.4s cubic-bezier(0.22,1,0.36,1) both',
        'fade-in': 'fade-in 0.3s ease-out both',
        glow: 'glow 2.5s ease-in-out infinite',
        'mesh-spin': 'mesh-spin 25s linear infinite',
        'evidence-pulse': 'evidence-pulse 1.2s cubic-bezier(0.22,1,0.36,1) 1',
        'dialog-in': 'dialog-in 0.18s cubic-bezier(0.22,1,0.36,1) both',
      },
      backgroundImage: {
        'grid-soft':
          'linear-gradient(rgb(var(--grid-line) / 1) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--grid-line) / 1) 1px, transparent 1px)',
        'radial-glow':
          'radial-gradient(circle at 50% 0%, rgb(var(--status-info) / 0.25), transparent 60%)',
        'gradient-brand':
          'linear-gradient(135deg, rgb(var(--status-info)) 0%, rgb(var(--accent-teal)) 50%, rgb(var(--accent-violet)) 100%)',
      },
    },
  },
  plugins: [animate],
};

export default config;
