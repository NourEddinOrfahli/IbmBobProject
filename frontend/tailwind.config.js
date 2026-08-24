/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        space: {
          bg: '#050712',
          900: '#080c1a',
          800: '#0c1120',
          700: '#101828',
          600: '#1a2540',
          500: '#243050',
          surface: 'rgba(255,255,255,0.03)',
          elevated: 'rgba(255,255,255,0.055)',
          border: '#1a2540',
          'border-light': '#243050',
        },
        pulsar: {
          blue:   '#00D9FF',
          violet: '#7A2CFF',
          pink:   '#FF2D9A',
          white:  '#F7FBFF',
        },
        text: {
          primary: '#F7FBFF',
          muted:   '#8BAAC8',
          faint:   '#3d5a80',
        },
        accent: {
          blue:   '#00D9FF',
          gold:   '#f5c842',
          green:  '#4ade80',
          red:    '#f87171',
          orange: '#fb923c',
          cyan:   '#00D9FF',
        },
      },
      fontFamily: {
        arabic: [
          'IBM Plex Sans Arabic',
          'Tahoma',
          'Arial',
          'sans-serif',
        ],
      },
      backgroundImage: {
        'pulsar-gradient': 'linear-gradient(135deg, #00D9FF, #7A2CFF, #FF2D9A)',
        'pulsar-gradient-h': 'linear-gradient(90deg, #00D9FF, #7A2CFF, #FF2D9A)',
        'pulsar-gradient-blue': 'linear-gradient(135deg, #00D9FF, #7A2CFF)',
      },
      animation: {
        'shimmer':       'shimmer 1.5s infinite',
        'fade-in':       'fadeIn 0.4s ease-out both',
        'fade-in-up':    'fadeInUp 0.5s ease-out both',
        'pulsar-core':   'pulsarCore 2.4s ease-in-out infinite',
        'pulsar-ring':   'pulsarRing 2.4s ease-in-out infinite',
        'expand-wave':   'expandWave 1.8s ease-out infinite',
        'spin-slow':     'spinSlow 1.2s linear infinite',
        'dot-pulse':     'dotPulse 1.4s ease-in-out infinite',
        'pulse-slow':    'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%':   { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulsarCore: {
          '0%, 100%': { opacity: '0.7', transform: 'scale(1)' },
          '50%':      { opacity: '1',   transform: 'scale(1.12)' },
        },
        pulsarRing: {
          '0%':   { transform: 'scale(0.9)', opacity: '0.6' },
          '50%':  { transform: 'scale(1.1)', opacity: '0.25' },
          '100%': { transform: 'scale(0.9)', opacity: '0.6' },
        },
        expandWave: {
          '0%':   { transform: 'scale(0.8)', opacity: '0.5' },
          '100%': { transform: 'scale(2.2)', opacity: '0' },
        },
        spinSlow: {
          to: { transform: 'rotate(360deg)' },
        },
        dotPulse: {
          '0%, 100%': { opacity: '0.25', transform: 'scale(0.85)' },
          '50%':      { opacity: '1',    transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
};
