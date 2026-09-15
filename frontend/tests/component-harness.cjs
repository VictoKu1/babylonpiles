const { readFileSync } = require('node:fs')
const ts = require('typescript')
const React = require('react')
for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const { outputText } = ts.transpileModule(readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true, target: ts.ScriptTarget.ES2022 },
      fileName: filename,
    })
    module._compile(outputText, filename)
  }
}

// A small hook renderer for exercising real component effects and event handlers.
// It does not emulate browser layout, downloads, or native iframe behavior.
function mount(Component, props = {}) {
  const slots = []
  let cursor = 0, tree, dirty = true
  const effects = []
  const internals = React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED
  const changed = (before, after) => !before || !after || after.some((value, i) => !Object.is(value, before[i]))
  const dispatcher = {
    useState(initial) {
      const i = cursor++
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial
      return [slots[i], value => {
        const next = typeof value === 'function' ? value(slots[i]) : value
        if (!Object.is(next, slots[i])) { slots[i] = next; dirty = true }
      }]
    },
    useRef(initial) { const i = cursor++; return slots[i] ||= { current: initial } },
    useMemo(factory, deps) {
      const i = cursor++
      if (!slots[i] || changed(slots[i].deps, deps)) slots[i] = { deps, value: factory() }
      return slots[i].value
    },
    useCallback(callback, deps) { return dispatcher.useMemo(() => callback, deps) },
    useEffect(effect, deps) {
      const i = cursor++
      if (!slots[i] || changed(slots[i].deps, deps)) {
        const previous = slots[i]
        slots[i] = { deps, cleanup: previous?.cleanup }
        effects.push(() => { previous?.cleanup?.(); slots[i].cleanup = effect() })
      }
    },
    useLayoutEffect(effect, deps) { dispatcher.useEffect(effect, deps) },
    useContext(context) {
      const router = require('react-router-dom')
      if (context === router.UNSAFE_LocationContext) return { location: { pathname: '/', search: '', hash: '', state: null, key: 'default' }, navigationType: 'POP' }
      if (context === router.UNSAFE_NavigationContext) return { basename: '/', navigator: {}, static: false }
      return context._currentValue
    },
  }
  function render() {
    cursor = 0; dirty = false
    const previous = internals.ReactCurrentDispatcher.current
    internals.ReactCurrentDispatcher.current = dispatcher
    try { tree = Component(props) } finally { internals.ReactCurrentDispatcher.current = previous }
    while (effects.length) effects.shift()()
  }
  return {
    get tree() { return tree },
    async flush() {
      for (let i = 0; i < 30; i++) {
        if (dirty) render()
        await new Promise(resolve => setImmediate(resolve))
        if (!dirty && !effects.length) return tree
      }
      throw new Error('Component did not settle')
    },
    unmount() { for (const slot of slots) slot?.cleanup?.() },
  }
}

function nodes(value, predicate = () => true) {
  if (Array.isArray(value)) return value.flatMap(child => nodes(child, predicate))
  if (!value || typeof value !== 'object') return []
  return [...(predicate(value) ? [value] : []), ...nodes(value.props?.children, predicate)]
}
function text(value) {
  if (Array.isArray(value)) return value.map(text).join(' ')
  if (value == null || typeof value === 'boolean') return ''
  if (typeof value !== 'object') return String(value)
  return text(value.props?.children)
}
function button(tree, label) {
  const found = nodes(tree, node => node.type === 'button' && text(node).trim() === label)[0]
  if (!found) throw new Error(`Missing button ${label}; rendered: ${text(tree)}`)
  return found
}
module.exports = { mount, nodes, text, button }
