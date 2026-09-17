import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#16120d', surface: '#1e1811', surface2: '#292116', surface3: '#382c1c',
        accent: { DEFAULT: '#8fb89a', tint: '#22301f', strong: '#b8dcc0' },
        accent2: { DEFAULT: '#d7929c', tint: '#3a2228' },
        text: '#f1e7d6', dim: '#c2b39c', muted: '#8a7c66',
        ok: '#8fb89a', yellow: '#e0b969', red: '#e08a8a',
        line: 'rgba(241,231,214,.10)', strong: 'rgba(241,231,214,.20)',
      },
      fontFamily: { display: ['Fraunces', 'Georgia', 'serif'], body: ['"Work Sans"', 'system-ui', 'sans-serif'], mono: ['"IBM Plex Mono"', 'monospace'] },
      borderRadius: { DEFAULT: '4px' },
      boxShadow: { card: '0 10px 26px rgba(0,0,0,.4)' },
    },
  },
  plugins: [],
} satisfies Config;
