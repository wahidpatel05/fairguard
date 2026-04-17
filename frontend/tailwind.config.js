/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3B82F6',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        'fg-green': '#22c55e',
        'fg-amber': '#f59e0b',
        'fg-red': '#ef4444',
        'fg-blue': '#3b82f6',
        'fg-surface': '#f8fafc',
        'fg-border': '#e2e8f0',
      },
    },
  },
  plugins: [],
}

