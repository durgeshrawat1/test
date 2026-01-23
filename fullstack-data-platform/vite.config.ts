import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // ⚠️ FIX: Allow your custom domain
    allowedHosts: [
      "app.nexavisioninc.com",
      "localhost",
      "127.0.0.1"
    ],
    host: '0.0.0.0', // This allows external access (e.g. via AWS IP)
    port: 5173,      // Default Vite port
  }
})
