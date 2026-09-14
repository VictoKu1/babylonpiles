const assert = require('node:assert/strict')
const { test } = require('node:test')
const { mount, nodes, text, button } = require('./component-harness.cjs')
const { Piles } = require('../src/pages/Piles.tsx')
const { HotspotClient } = require('../src/pages/HotspotClient.tsx')
const { Updates } = require('../src/pages/Updates.tsx')
const { Dashboard } = require('../src/pages/Dashboard.tsx')
const { System } = require('../src/pages/System.tsx')
const { Sidebar } = require('../src/components/Sidebar.tsx')
const Browse = require('../src/pages/Browse.tsx').default

function environment(t, fetcher) {
  const alerts = []
  t.mock.method(globalThis, 'fetch', fetcher)
  t.mock.method(globalThis, 'setInterval', () => 0)
  t.mock.method(globalThis, 'clearInterval', () => {})
  globalThis.window = { alert: message => alerts.push(message) }
  globalThis.alert = window.alert
  t.after(() => { delete globalThis.window; delete globalThis.alert })
  return alerts
}
const ok = data => Response.json({ success: true, data })
const file = { name: 'book.zim', url: 'https://example.org/book.zim', is_dir: false, size: 100 }
async function browser(t, fetcher) {
  environment(t, fetcher)
  const parent = mount(Piles)
  await parent.flush()
  button(parent.tree, 'Quick Add').props.onClick()
  await parent.flush()
  const child = nodes(parent.tree, node => typeof node.type === 'function' && node.props.onDownload)[0]
  const view = mount(child.type, child.props)
  t.after(() => { parent.unmount(); view.unmount() })
  await view.flush()
  nodes(view.tree, node => node.type === 'select')[0].props.onChange({ target: { value: 'Library' } })
  return view
}

test('source listing failures remain recoverable instead of replacing the tree with an error payload', async t => {
  let failed = true
  const view = await browser(t, async url => {
    if (url === '/api/v1/piles/') return ok([])
    if (url.endsWith('sources-list')) return Response.json({ Library: ['https://example.org/', ''] })
    return failed ? Response.json({ detail: 'Repository unavailable' }, { status: 400 }) : Response.json({ items: [file] })
  })
  await view.flush()
  assert.match(text(view.tree), /Repository unavailable|Unable to load|Failed to load/)
  failed = false
  await button(view.tree, 'Retry').props.onClick()
  await view.flush()
  assert.match(text(view.tree), /book.zim/)
})

test('selecting an unloaded folder resolves every descendant before download confirmation', async t => {
  const folder = { name: 'books', url: 'https://example.org/books/', is_dir: true, size: null }
  let releaseChildren
  const children = new Promise(resolve => { releaseChildren = resolve })
  const view = await browser(t, async url => {
    if (url === '/api/v1/piles/') return ok([])
    if (url.endsWith('sources-list')) return Response.json({ Library: ['https://example.org/', ''] })
    if (new URL(url, 'http://test').searchParams.get('url') === folder.url) { await children; return Response.json({ items: [file] }) }
    return Response.json({ items: [{ ...folder }] })
  })
  await view.flush()
  const checkboxes = nodes(view.tree, node => typeof node.type === 'function' && node.props.onChange)
  checkboxes.at(-1).props.onChange({ target: { checked: true } })
  releaseChildren()
  await view.flush()
  assert.equal(nodes(view.tree, node => typeof node.type === 'function' && node.props.onChange)[0].props.checked, true, 'Select All reflects inherited selection after children load')
  await button(view.tree, 'Download Selected').props.onClick()
  await view.flush()
  assert.match(text(view.tree), /book.zim/)
  assert.match(text(view.tree), /1\s+file\(s\)/)
})

test('Quick Add downloads successfully created IDs and reports per-file failures', async t => {
  const downloaded = []
  const alerts = environment(t, async (url, options) => {
    if (options?.method === 'POST' && url === '/api/v1/piles/') {
      return JSON.parse(options.body).display_name === 'duplicate.zim'
        ? Response.json({ detail: 'Pile already exists' }, { status: 400 }) : ok({ id: 42 })
    }
    if (url.endsWith('/download-source')) { downloaded.push(url); return ok({ id: 42, file_path: 'book.zim' }) }
    return ok([])
  })
  const view = mount(Piles)
  await view.flush()
  button(view.tree, 'Quick Add').props.onClick()
  await view.flush()
  const child = nodes(view.tree, node => typeof node.type === 'function' && node.props.onDownload)[0]
  await child.props.onDownload([file, { ...file, name: 'duplicate.zim' }])
  await view.flush()
  assert.deepEqual(downloaded, ['/api/v1/piles/42/download-source'])
  assert.match([...alerts, text(view.tree)].join(' '), /duplicate.zim.*Pile already exists/s)
  view.unmount()
})

test('Quick Add waits for each transfer and continues after a failed download', async t => {
  let active = 0, peak = 0, id = 0
  const completed = []
  environment(t, async (url, options) => {
    if (options?.method !== 'POST') return ok([])
    if (url === '/api/v1/piles/') return ok({ id: ++id })
    active++; peak = Math.max(peak, active)
    await new Promise(resolve => setImmediate(resolve))
    active--
    if (url.includes('/1/')) return Response.json({ detail: 'Source connection lost' }, { status: 502 })
    completed.push(url)
    return ok({ file_path: 'saved.zim' })
  })
  const view = mount(Piles)
  await view.flush()
  button(view.tree, 'Quick Add').props.onClick()
  await view.flush()
  const child = nodes(view.tree, node => typeof node.type === 'function' && node.props.onDownload)[0]
  await child.props.onDownload([file, { ...file, name: 'second.zim' }, { ...file, name: 'third.zim' }])
  await view.flush()
  assert.equal(peak, 1)
  assert.deepEqual(completed, ['/api/v1/piles/2/download-source', '/api/v1/piles/3/download-source'])
  assert.match(text(view.tree), /Downloaded\s+2\s+file/)
  assert.match(text(view.tree), /book.zim: Source connection lost/)
  view.unmount()
})

test('source search retains ancestors of deeper matching files', async t => {
  const first = { name: 'collection', url: 'https://example.org/collection/', is_dir: true, size: null }
  const second = { name: 'archive', url: `${first.url}archive/`, is_dir: true, size: null }
  const view = await browser(t, async url => {
    if (url === '/api/v1/piles/') return ok([])
    if (url.endsWith('sources-list')) return Response.json({ Library: ['https://example.org/', ''] })
    const target = new URL(url, 'http://test').searchParams.get('url')
    return Response.json({ items: target === first.url ? [{ ...second }] : target === second.url ? [file] : [{ ...first }] })
  })
  await view.flush()
  nodes(view.tree, node => node.type === 'input' && node.props.placeholder === 'Search files/folders...')[0].props.onChange({ target: { value: 'book' } })
  await view.flush()
  nodes(view.tree, node => node.type === 'button' && node.props.title === 'Search')[0].props.onClick()
  await view.flush()
  assert.match(text(view.tree), /collection/)
  assert.match(text(view.tree), /book.zim/)
})

test('empty source directories remain visible without an active filter', async t => {
  const folder = { name: 'empty', url: 'https://example.org/empty/', is_dir: true, size: null }
  const view = await browser(t, async url => {
    if (url === '/api/v1/piles/') return ok([])
    if (url.endsWith('sources-list')) return Response.json({ Library: ['https://example.org/', ''] })
    return Response.json({ items: new URL(url, 'http://test').searchParams.get('url') === folder.url ? [] : [folder] })
  })
  await view.flush()
  assert.match(text(view.tree), /empty/)
})

test('public content retry clears the prior error after a successful response', async t => {
  let failed = true
  environment(t, async () => failed ? new Response(null, { status: 500 }) : ok({ files: [{ ...file, size_formatted: '100 B' }] }))
  const view = mount(HotspotClient)
  await view.flush()
  failed = false
  await button(view.tree, 'Retry').props.onClick()
  await view.flush()
  assert.match(text(view.tree), /book.zim/)
  assert.doesNotMatch(text(view.tree), /Failed to load public content/)
})

test('public upload request retains submitted details without fabricated network identity', async t => {
  let submitted
  environment(t, async (url, options) => {
    if (options?.method === 'POST') { submitted = JSON.parse(options.body); return ok({ request_id: 'request-1', status: 'pending', message: 'Waiting for review' }) }
    return ok({ files: [] })
  })
  const view = mount(HotspotClient)
  await view.flush()
  button(view.tree, 'Request Upload').props.onClick()
  await view.flush()
  const inputs = nodes(view.tree, node => node.type === 'input')
  inputs[0].props.onChange({ target: { value: 'notes.txt' } })
  await view.flush()
  nodes(view.tree, node => node.type === 'input')[1].props.onChange({ target: { value: 'Reader' } })
  await view.flush()
  await nodes(view.tree, node => node.type === 'form')[0].props.onSubmit({ preventDefault() {} })
  await view.flush()
  assert.deepEqual(submitted, { filename: 'notes.txt', editor_name: 'Reader' })
  assert.match(text(view.tree), /notes.txt/)
  assert.match(text(view.tree), /Reader/)
})

const job = id => ({ id, provider: 'test', variant: String(id), destination_subpath: 'test', enabled: true, schedule_enabled: true, schedule_frequency: 'monthly', schedule_day: 31, schedule_time_utc: '02:00', status: 'idle', last_run_at: null, next_run_at: null, latest_run: null })
test('switching monthly to weekly uses a valid weekday', async t => {
  environment(t, async url => ok(url.endsWith('providers') ? [] : [job(1)]))
  const view = mount(Updates)
  await view.flush()
  const frequency = nodes(view.tree, node => node.type === 'select' && node.props.value === 'monthly')[0]
  frequency.props.onChange({ target: { value: 'weekly' } })
  await view.flush()
  const day = nodes(view.tree, node => node.type === 'select' && typeof node.props.value === 'number')[0]
  assert.ok(day.props.value >= 0 && day.props.value <= 6, `Invalid weekday ${day.props.value}`)
})

test('switching Sunday weekly schedule to monthly uses a valid calendar day', async t => {
  environment(t, async url => ok(url.endsWith('providers') ? [] : [{ ...job(1), schedule_frequency: 'weekly', schedule_day: 0 }]))
  const view = mount(Updates)
  await view.flush()
  nodes(view.tree, node => node.type === 'select' && node.props.value === 'weekly')[0].props.onChange({ target: { value: 'monthly' } })
  await view.flush()
  assert.equal(nodes(view.tree, node => node.type === 'input' && node.props.type === 'number')[0].props.value, 1)
})

test('refresh preserves unsaved edits to other mirror jobs', async t => {
  environment(t, async url => ok(url.endsWith('providers') ? [] : [job(1), job(2)]))
  const view = mount(Updates)
  await view.flush()
  nodes(view.tree, node => node.type === 'input' && node.props.type === 'time')[1].props.onChange({ target: { value: '17:45' } })
  await view.flush()
  button(view.tree, 'Refresh').props.onClick()
  await view.flush()
  assert.equal(nodes(view.tree, node => node.type === 'input' && node.props.type === 'time')[1].props.value, '17:45')
})

test('refresh updates untouched mirror settings while preserving edited jobs', async t => {
  let refreshed = false
  environment(t, async url => ok(url.endsWith('providers') ? [] : [
    { ...job(1), schedule_time_utc: refreshed ? '08:30' : '02:00' }, job(2),
  ]))
  const view = mount(Updates)
  await view.flush()
  nodes(view.tree, node => node.type === 'input' && node.props.type === 'time')[1].props.onChange({ target: { value: '17:45' } })
  await view.flush()
  refreshed = true
  button(view.tree, 'Refresh').props.onClick()
  await view.flush()
  const times = nodes(view.tree, node => node.type === 'input' && node.props.type === 'time').map(node => node.props.value)
  assert.deepEqual(times, ['08:30', '17:45'])
})

test('legacy UTC mirror timestamps retain their instant in a non-UTC timezone', async t => {
  const previous = process.env.TZ
  process.env.TZ = 'Asia/Jerusalem'
  t.after(() => { if (previous === undefined) delete process.env.TZ; else process.env.TZ = previous })
  environment(t, async url => ok(url.endsWith('providers') ? [] : [{ ...job(1), next_run_at: '2026-09-13T12:00:00' }]))
  const view = mount(Updates)
  await view.flush()
  assert.ok(text(view.tree).includes(new Date('2026-09-13T12:00:00Z').toLocaleTimeString()), text(view.tree))
})

test('dashboard uses backend content bytes once and calculates percentage before formatting', async t => {
  const content = 500 * 1024 ** 2, total = 1024 ** 4
  environment(t, async url => {
    if (url === '/api/v1/piles/') return Response.json({ data: [{ id: 1, name: 'book', display_name: 'Book', category: 'education', source_type: 'kiwix', file_path: 'book.zim', file_size: content }], total: 1 })
    if (url.includes('/files?')) return Response.json({ items: [{ name: 'book.zim', size: content }] })
    if (url.endsWith('/storage')) return ok({ content_size_bytes: content, total_bytes: total, available_bytes: total - content })
    if (url.endsWith('/metrics')) return ok({ disk: { total_bytes: total, used_bytes: content, free_bytes: total - content } })
    if (url.endsWith('/hotspot/status')) return ok({ is_running: false, connected_devices: [], pending_requests: [], user_config: {} })
    return ok({ current_mode: 'learn', internet_available: true })
  })
  const view = mount(Dashboard)
  await view.flush()
  assert.match(text(view.tree), /500 MB/)
  assert.doesNotMatch(text(view.tree), /1000 MB/)
  const bar = nodes(view.tree, node => node.props.className?.includes('bg-blue-500') && node.props.style?.width)[0]
  assert.equal(parseFloat(bar.props.style.width), content / total * 100)
  view.unmount()
})

test('dashboard renders empty content with available storage space', async t => {
  environment(t, async url => {
    if (url === '/api/v1/piles/') return Response.json({ success: true, data: [], total: 0 })
    if (url.endsWith('/storage')) return ok({ content_size_bytes: 0, total_bytes: 8 * 1024 ** 3, available_bytes: 7 * 1024 ** 3, used_bytes: 0, piles_size_bytes: 0, usage_percent: 0, no_storage_allocated: true })
    if (url.endsWith('/metrics')) return ok({ disk: { total_bytes: 4 * 1024 ** 3, used_bytes: 2 * 1024 ** 3, free_bytes: 2 * 1024 ** 3 } })
    if (url.endsWith('/hotspot/status')) return ok({ is_running: false, connected_devices: [], pending_requests: [], user_config: {} })
    return ok({ current_mode: 'learn', internet_available: true })
  })
  const view = mount(Dashboard)
  t.after(() => view.unmount())
  await view.flush()
  assert.doesNotMatch(text(view.tree), /Failed to load dashboard data/)
  assert.match(text(view.tree), /Content Used\s+0 B/)
  assert.match(text(view.tree), /Available Space\s+7 GB/)
  assert.equal(nodes(view.tree, node => node.props.className?.includes('bg-blue-500') && node.props.style?.width).length, 0)
})

test('system screen renders current backend metrics and network addresses', async t => {
  environment(t, async url => {
    if (url.endsWith('/metrics')) return ok({ cpu: { usage_percent: 37 }, memory: { usage_percent: 61 }, disk: { usage_percent: 42 } })
    if (url.endsWith('/network')) return ok({ eth0: { addresses: ['10.2.3.4'] }, total_connections: 2 })
    return ok({ current_mode: 'learn', internet_available: false })
  })
  const view = mount(System)
  await view.flush()
  assert.match(text(view.tree), /Learn/)
  assert.match(text(view.tree), /37%/)
  assert.match(text(view.tree), /10.2.3.4/)
  assert.doesNotMatch(text(view.tree), /192.168.1.100/)
  view.unmount()
})

test('sidebar reads wrapped status and does not confuse offline internet with an unreachable backend', async t => {
  environment(t, async url => url.endsWith('/gitinfo') ? Response.json({ version: 'v1', build: 'today' }) : ok({ current_mode: 'learn', internet_available: false }))
  const view = mount(Sidebar)
  await view.flush()
  button(view.tree, 'Software Information').props.onClick()
  await view.flush()
  assert.match(text(view.tree), /Online/)
  assert.match(text(view.tree), /Learn/)
  view.unmount()
})

test('file viewer download links use the query endpoint and preserve path encoding', async t => {
  environment(t, async url => {
    if (url.includes('/view/')) return ok({ view_type: 'text', can_view: true, file_size: 100 })
    if (url.endsWith('download-status')) return ok({})
    return Response.json({ path: '', items: [{ name: 'notes #1.txt', is_dir: false, size: 100 }] })
  })
  const view = mount(Browse)
  await view.flush()
  const viewButton = nodes(view.tree, node => node.type === 'button' && /View/.test(text(node)) && node.props.onClick).at(-1)
  assert.ok(viewButton, 'File has a view action')
  await viewButton.props.onClick()
  await view.flush()
  const links = nodes(view.tree, node => node.type === 'a' && /Download/.test(text(node)))
  assert.ok(links.length)
  for (const link of links) assert.equal(link.props.href, '/api/v1/files/download?path=notes%20%231.txt')
  view.unmount()
})
