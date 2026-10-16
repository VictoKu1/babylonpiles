const assert = require('node:assert/strict')
const { test } = require('node:test')
const { mount, text } = require('./component-harness.cjs')
const { AuthProvider, AuthContext } = require('../src/contexts/AuthContext.tsx')
const { RequireAdmin } = require('../src/components/RequireAdmin.tsx')
const { Login } = require('../src/pages/Login.tsx')
const { loginSession } = require('../src/api/auth.ts')

const admin = { id: 1, username: 'operator', role: 'admin', is_admin: true, is_active: true }
const ok = data => Response.json({ success: true, data })

async function session(t, fetcher) {
  globalThis.window = { location: { origin: 'http://testserver' } }
  t.after(() => { delete globalThis.window })
  t.mock.method(globalThis, 'fetch', fetcher)
  const view = mount(AuthProvider, { children: null })
  t.after(() => view.unmount())
  await view.flush()
  return view
}

test('a later private 401 clears the mounted session without retrying or consuming the response', async t => {
  const requests = []
  const view = await session(t, async (url, options) => {
    requests.push([url, options])
    return url === '/api/v1/auth/me' ? ok(admin) : Response.json({ detail: 'Expired session' }, { status: 401 })
  })
  assert.equal(view.tree.props.value.user.id, 1)
  const options = { method: 'POST', body: 'unchanged-body' }
  const response = await fetch('/api/v1/files/mkdir', options)
  assert.equal(response.status, 401)
  assert.deepEqual(await response.json(), { detail: 'Expired session' })
  await view.flush()
  assert.equal(view.tree.props.value.user, null)
  assert.equal(view.tree.props.value.isAuthenticated, false)
  assert.equal(view.tree.props.value.sessionExpired, true)
  assert.deepEqual(requests, [['/api/v1/auth/me', { credentials: 'same-origin', cache: 'no-store' }], ['/api/v1/files/mkdir', options]])
})

test('public, external, login, and non-401 failures do not clear an existing session', async t => {
  const view = await session(t, async url => {
    if (url === '/api/v1/auth/me') return ok(admin)
    if (url === '/api/v1/system/network-error') throw new TypeError('Network unavailable')
    return new Response(null, { status: url.endsWith('/forbidden') ? 403 : url.endsWith('/limited') ? 429 : 401 })
  })
  for (const url of [
    '/api/v1/auth/login', '/api/v1/auth/logout', '/api/v1/public/content',
    '/api/v1/system/hotspot/public-content', '/api/v1/system/hotspot/public-content/',
    '/api/v1/system/hotspot/download/book.zim', '/api/v1/system/hotspot/request-upload',
    'https://external.invalid/api/v1/files', '/api/v1/files/forbidden', '/api/v1/files/limited',
  ]) await fetch(url)
  await assert.rejects(fetch('/api/v1/system/network-error'), /Network unavailable/)
  await view.flush()
  assert.equal(view.tree.props.value.user.id, 1)
  assert.equal(view.tree.props.value.sessionExpired, false)
})

test('private absolute URLs, Request inputs, and encoded paths also expire the session', async t => {
  const view = await session(t, async url => url === '/api/v1/auth/me' ? ok(admin) :
    url === '/api/v1/auth/login' ? ok({ user: admin }) : new Response(null, { status: 401 }))
  for (const input of [
    new URL('http://testserver/api/v1/piles/'),
    new Request('http://testserver/api/v1/storage/health'),
    '/api/v1/%66iles?path=archive',
  ]) {
    await fetch(input)
    await view.flush()
    assert.equal(view.tree.props.value.user, null)
    await view.tree.props.value.login('operator', 'password')
    await view.flush()
    assert.equal(view.tree.props.value.sessionExpired, false)
  }
})

test('a delayed 401 from an old session cannot clear a newly signed-in session', async t => {
  let finishOldRequest
  const view = await session(t, async url => {
    if (url === '/api/v1/auth/me') return ok(admin)
    if (url === '/api/v1/auth/login') return ok({ user: { ...admin, id: 2 } })
    return new Promise(resolve => { finishOldRequest = resolve })
  })
  const oldRequest = fetch('/api/v1/system/status')
  await view.tree.props.value.login('second-admin', 'password')
  finishOldRequest(new Response(null, { status: 401 }))
  await oldRequest
  await view.flush()
  assert.equal(view.tree.props.value.user.id, 2)
  assert.equal(view.tree.props.value.sessionExpired, false)
})

test('initial anonymous sessions do not claim to have expired and unmount restores fetch', async t => {
  const view = await session(t, async () => new Response(null, { status: 401 }))
  assert.equal(view.tree.props.value.user, null)
  assert.equal(view.tree.props.value.sessionExpired, false)
  const monitored = globalThis.fetch
  view.unmount()
  assert.notEqual(globalThis.fetch, monitored)
})

test('the route guard retains the path, search, and fragment for signing in again', async t => {
  t.mock.property(AuthContext, '_currentValue', { user: null, loading: false, sessionExpired: true })
  const view = mount(RequireAdmin, {}, { location: { pathname: '/browse', search: '?path=books', hash: '#preview' } })
  await view.flush()
  assert.equal(view.tree.props.to, '/login')
  assert.equal(view.tree.props.state.from, '/browse?path=books#preview')
})

test('sign-in shows an expired-session message and rejects external or login-loop return paths', async t => {
  t.mock.property(AuthContext, '_currentValue', { user: null, loading: false, sessionExpired: true })
  const expired = mount(Login)
  await expired.flush()
  assert.match(text(expired.tree), /session.*expired.*sign in again/i)
  AuthContext._currentValue = { user: admin, loading: false, sessionExpired: false }
  for (const from of ['https://external.invalid/', '//external.invalid/', '/\\external.invalid/', '/login?next=/browse', '/login#again', '/a/../login', '/%2fexternal.invalid/', '/\n/external.invalid/']) {
    const view = mount(Login, {}, { location: { state: { from } } })
    await view.flush()
    assert.equal(view.tree.props.to, '/', from)
  }
  const destination = mount(Login, {}, { location: { state: { from: '/browse?path=books#preview' } } })
  await destination.flush()
  assert.equal(destination.tree.props.to, '/browse?path=books#preview')
})

test('rate-limited sign-in reports Retry-After without retrying credentials', async t => {
  let attempts = 0
  t.mock.method(globalThis, 'fetch', async () => {
    attempts += 1
    return new Response(null, { status: 429, headers: { 'Retry-After': '45' } })
  })
  await assert.rejects(loginSession('operator', 'password'), /too many.*45 seconds/i)
  assert.equal(attempts, 1)
})
