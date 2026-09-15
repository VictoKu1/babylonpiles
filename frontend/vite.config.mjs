import { defineConfig } from 'vite'

const proxy = {
  '/api': {
    target: process.env.BACKEND_PROXY_URL || 'http://127.0.0.1:8080',
    // Keep the browser's Host so the backend can validate mutation Origins.
    changeOrigin: false,
  },
}

export default defineConfig({
  server: { proxy },
  preview: { proxy },
})
