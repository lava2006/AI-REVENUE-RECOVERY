/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: '#f4f4f6',
          subtle: '#e9ecef',
          surface: '#ffffff',
          panel: '#f8fafc',
          border: '#e2e8f0',
          borderDark: '#cbd5e1',
        },
        ink: {
          DEFAULT: '#0f172a',
          secondary: '#334155',
          muted: '#64748b',
          faint: '#94a3b8',
        },
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          900: '#312e81',
        },
        fintech: {
          dark: '#0f172a',
          card: '#ffffff',
          border: '#e2e8f0',
          borderLight: '#cbd5e1',
          accent: '#4f46e5',
          accentHover: '#4338ca',
          success: '#059669',
          warning: '#d97706',
          danger: '#dc2626',
          muted: '#64748b',
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        'elevated': '0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
        'popover': '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
