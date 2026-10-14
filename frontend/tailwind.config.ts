import type { Config } from 'tailwindcss';

export default <Config>{
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        midnight: '#0a0f2c', // deep navy for sidebar/header
        teal: '#2dd4bf', // teal accent for KPI values
        emerald: '#10b981', // emerald for success states
      },
    },
  },
  plugins: [],
} as const;
