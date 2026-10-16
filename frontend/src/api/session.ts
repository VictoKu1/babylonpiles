function isPrivateRequest(input: RequestInfo | URL, origin: string): boolean {
  try {
    const url = new URL(typeof input === 'string' ? input : input instanceof URL ? input.href : input.url, origin)
    if (url.origin !== origin) return false
    const path = decodeURIComponent(url.pathname).replace(/\/+$/, '')
    if (path === '/api/v1/system/hotspot/public-content' || path === '/api/v1/system/hotspot/request-upload' ||
        /^\/api\/v1\/system\/hotspot\/download(?:\/|$)/.test(path)) return false
    return path === '/api/v1/auth/me' || /^\/api\/v1\/(?:system|piles|updates|mirrors|files|storage)(?:\/|$)/.test(path)
  } catch {
    return false
  }
}

// All management pages use fetch directly. Observe responses once without changing
// bodies, retrying mutations, or intercepting public content and external services.
export function monitorSessionRequests(origin: string, sessionVersion: () => number, onExpired: () => void): () => void {
  const originalFetch = globalThis.fetch
  let active = true
  const monitoredFetch: typeof fetch = async (input, options) => {
    const version = sessionVersion()
    const response = await originalFetch.call(globalThis, input, options)
    if (active && response.status === 401 && version === sessionVersion() && isPrivateRequest(input, origin)) {
      onExpired()
    }
    return response
  }
  globalThis.fetch = monitoredFetch
  return () => {
    active = false
    if (globalThis.fetch === monitoredFetch) globalThis.fetch = originalFetch
  }
}

export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || /[\\\u0000-\u001f\u007f]/.test(value)) return '/'
  try {
    const url = new URL(value, 'http://session.invalid')
    const path = decodeURIComponent(url.pathname)
    if (url.origin !== 'http://session.invalid' || path.startsWith('//') || /[\\\u0000-\u001f\u007f]/.test(path) ||
        path.replace(/\/+$/, '') === '/login') return '/'
    return url.pathname + url.search + url.hash
  } catch {
    return '/'
  }
}
