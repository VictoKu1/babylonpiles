const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { test } = require('node:test')
const ts = require('typescript')
// This suite renders the production markup without mounting browser-only effects.
process.env.NODE_ENV = 'production'
const React = require('react')
const { renderToStaticMarkup } = require('react-dom/server')
const { MemoryRouter } = require('react-router-dom')

// Run the real TypeScript/React components with the project's existing dependencies.
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const { outputText } = ts.transpileModule(readFileSync(filename, 'utf8'), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.React,
        esModuleInterop: true,
        target: ts.ScriptTarget.ES2022,
      },
      fileName: filename,
    })
    module._compile(outputText, filename)
  }
}

const admin = { id: 1, username: 'operator', role: 'admin', is_admin: true, is_active: true }
const member = { id: 2, username: 'reader', role: 'user', is_admin: false, is_active: true }
const h = React.createElement

function renderApp(path) {
  const App = require('../src/App.tsx').default
  return renderToStaticMarkup(h(MemoryRouter, { initialEntries: [path] }, h(App)))
}

test('private routes do not mount admin navigation before session verification', () => {
  for (const path of ['/', '/piles', '/system', '/updates', '/browse', '/zim-viewer/book.zim']) {
    const html = renderApp(path)
    assert.doesNotMatch(html, /<nav[ >]/, `admin navigation leaked for ${path}`)
    assert.match(html, /Checking session/)
  }
})

test('the hotspot route stays available without an administrator session', () => {
  assert.match(renderApp('/hotspot'), /Loading public content/)
})

test('the route guard rejects guests, ordinary users, and inactive administrators', () => {
  const { AuthContext } = require('../src/contexts/AuthContext.tsx')
  const { RequireAdmin } = require('../src/components/RequireAdmin.tsx')
  const { Routes, Route } = require('react-router-dom')
  for (const user of [null, member, { ...admin, is_active: false }, admin]) {
    const html = renderToStaticMarkup(h(AuthContext.Provider, { value: { user, loading: false } },
      h(MemoryRouter, { initialEntries: ['/private'] },
        h(Routes, null, h(Route, { element: h(RequireAdmin) },
          h(Route, { path: '/private', element: h('p', null, 'Private administrator controls') }))))))
    assert.equal(html.includes('Private administrator controls'), user === admin)
  }
})

test('login sends JSON credentials to the same origin and returns only the verified user', async (t) => {
  const { loginSession } = require('../src/api/auth.ts')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/v1/auth/login')
    assert.equal(options.method, 'POST')
    assert.equal(options.credentials, 'same-origin')
    assert.equal(options.headers['Content-Type'], 'application/json')
    assert.deepEqual(JSON.parse(options.body), { username: 'operator', password: 'correct password' })
    return Response.json({ success: true, data: { user: admin, access_token: 'do-not-persist', token_type: 'bearer' } })
  })
  assert.deepEqual(await loginSession('operator', 'correct password'), admin)
})

test('failed or malformed login responses never establish a session', async (t) => {
  const { loginSession } = require('../src/api/auth.ts')
  for (const response of [
    Response.json({ detail: 'Incorrect username or password' }, { status: 401 }),
    Response.json({ success: false, data: { user: admin } }),
    Response.json({ success: true, data: { access_token: 'token-only' } }),
    Response.json({ success: true, data: { user: { ...admin, is_active: false } } }),
  ]) {
    t.mock.method(globalThis, 'fetch', async () => response)
    await assert.rejects(loginSession('operator', 'incorrect'))
    t.mock.restoreAll()
  }
})

test('refresh validates the cookie session and treats an expired session as signed out', async (t) => {
  const { readSession } = require('../src/api/auth.ts')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/v1/auth/me')
    assert.equal(options.credentials, 'same-origin')
    assert.equal(options.cache, 'no-store')
    return Response.json({ success: true, data: admin })
  })
  assert.deepEqual(await readSession(), admin)
  t.mock.restoreAll()
  t.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 401 }))
  assert.equal(await readSession(), null)
})

test('logout clears the server cookie and reports failures instead of claiming success', async (t) => {
  const { logoutSession } = require('../src/api/auth.ts')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, '/api/v1/auth/logout')
    assert.equal(options.method, 'POST')
    assert.equal(options.credentials, 'same-origin')
    return Response.json({ success: true })
  })
  await logoutSession()
  t.mock.restoreAll()
  t.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 500 }))
  await assert.rejects(logoutSession())
})

test('remote source metadata renders executable HTML as escaped text in every field', () => {
  const { SourceInfo } = require('../src/components/SourceInfo.tsx')
  const attack = '<img src=x onerror=alert(1)><script>alert(2)</script>'
  const info = { found: true, title: attack, description: attack, language: attack, creator: attack, publisher: attack }
  const html = renderToStaticMarkup(h(SourceInfo, { info }))
  assert.doesNotMatch(html, /<img|<script|<svg|onerror="/i)
  assert.equal((html.match(/&lt;img src=x onerror=alert\(1\)&gt;/g) || []).length, 5)
  assert.equal((html.match(/&lt;script&gt;alert\(2\)&lt;\/script&gt;/g) || []).length, 5)
})

test('source metadata handles missing and malformed fields without an HTML fallback', () => {
  const { SourceInfo } = require('../src/components/SourceInfo.tsx')
  assert.match(renderToStaticMarkup(h(SourceInfo, { info: { found: false } })), /No information found/)
  const html = renderToStaticMarkup(h(SourceInfo, { info: { found: true, title: { malicious: 'object' } } }))
  assert.match(html, /Title:/)
  assert.doesNotMatch(html, /\[object Object\]/)
})
