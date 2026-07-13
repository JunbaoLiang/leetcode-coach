import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Dev-time proxy so the frontend can call the FastAPI backend without CORS pain
      '/api': 'http://localhost:8000',
    },
  },
})
