import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dashboard talks to the FastAPI backend directly over ws://host:8000/ws
// (CORS is open on the backend), so no dev proxy is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // expose on the LAN so you can run it on a second display/device
  },
})
