const assert = require('node:assert/strict')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { resolve } = require('node:path')
const { pathToFileURL } = require('node:url')
const { test } = require('node:test')

test('same-origin proxy preserves CSRF headers, session cookies, and private media ranges', async (t) => {
  const requests = []
  const backend = createServer((request, response) => {
    requests.push({ method: request.method, url: request.url, headers: request.headers })
    if (request.url === '/api/v1/auth/login') {
      response.setHeader('Set-Cookie', 'session=test; HttpOnly; SameSite=Strict; Path=/')
      response.setHeader('Content-Type', 'application/json')
      response.end(JSON.stringify({ success: true }))
    } else {
      response.writeHead(206, { 'Content-Type': 'application/pdf', 'Content-Range': 'bytes 0-3/20' })
      response.end('%PDF')
    }
  })
  backend.listen(0, '127.0.0.1')
  await once(backend, 'listening')
  t.after(() => new Promise(resolve => backend.close(resolve)))

  const previousTarget = process.env.BACKEND_PROXY_URL
  process.env.BACKEND_PROXY_URL = `http://127.0.0.1:${backend.address().port}`
  t.after(() => {
    if (previousTarget === undefined) delete process.env.BACKEND_PROXY_URL
    else process.env.BACKEND_PROXY_URL = previousTarget
  })
  const { createServer: createViteServer } = await import(pathToFileURL(require.resolve('vite')).href)
  const frontend = await createViteServer({
    root: resolve(__dirname, '..'),
    configFile: resolve(__dirname, '../vite.config.mjs'),
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    logLevel: 'silent',
  })
  await frontend.listen()
  t.after(() => frontend.close())
  const origin = `http://127.0.0.1:${frontend.httpServer.address().port}`

  const login = await fetch(`${origin}/api/v1/auth/login`, {
    method: 'POST',
    headers: { Origin: origin, 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'operator', password: 'test' }),
  })
  assert.equal(login.status, 200)
  assert.equal(login.headers.get('set-cookie'), 'session=test; HttpOnly; SameSite=Strict; Path=/')
  assert.equal(requests[0].headers.host, new URL(origin).host)
  assert.equal(requests[0].headers.origin, origin)

  const preview = await fetch(`${origin}/api/v1/files/preview/report.pdf`, {
    headers: { Cookie: 'session=test', Range: 'bytes=0-3' },
  })
  assert.equal(preview.status, 206)
  assert.equal(await preview.text(), '%PDF')
  assert.equal(preview.headers.get('content-range'), 'bytes 0-3/20')
  assert.equal(requests[1].headers.cookie, 'session=test')
  assert.equal(requests[1].headers.range, 'bytes=0-3')
})
