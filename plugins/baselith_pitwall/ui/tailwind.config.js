/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: {
          1: 'var(--surface-1)',
          2: 'var(--surface-2)',
          3: 'var(--surface-3)',
        },
        hair: 'var(--hairline)',
        'hair-strong': 'var(--hairline-strong)',
        ink: 'var(--text)',
        dim: 'var(--text-dim)',
        faint: 'var(--text-faint)',
        ember: 'var(--ember)',
        'ember-deep': 'var(--ember-deep)',
        go: 'var(--go)',
        caution: 'var(--caution)',
        danger: 'var(--danger)',
        info: 'var(--info)',
        violet: 'var(--violet)',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        xl: '14px',
        '2xl': '18px',
      },
      boxShadow: {
        panel: 'var(--shadow-panel)',
        glow: '0 0 22px -6px var(--tw-shadow-color)',
      },
    },
  },
  plugins: [],
};
