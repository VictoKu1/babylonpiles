import { defineConfig } from 'vite'

const proxy = {
  '/api': {
    target: process.env.BACKEND_PROXY_URL || 'http://127.0.0.1:8080',
    // Keep the browser's Host so the backend can validate mutation Origins.
    changeOrigin: false,
    configure(proxy) {
      proxy.on('proxyReq', (proxyRequest, request) => {
        // Never append browser-supplied forwarding headers. The backend trusts
        // this single address only when the connection is from this proxy.
        proxyRequest.removeHeader('forwarded')
        proxyRequest.removeHeader('x-real-ip')
        proxyRequest.removeHeader('x-forwarded-for')
        if (request.socket.remoteAddress) {
          proxyRequest.setHeader('X-Forwarded-For', request.socket.remoteAddress)
        }
      })
    },
  },
}

export default defineConfig({
  server: { proxy },
  preview: { proxy },
})
