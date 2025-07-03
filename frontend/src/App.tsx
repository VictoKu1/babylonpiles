import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Piles } from './pages/Piles'
import { System } from './pages/System'
import { Updates } from './pages/Updates'
import Browse from './pages/Browse'
import { ZimViewer } from './pages/ZimViewer'
import { Login } from './pages/Login'
import { AuthProvider } from './contexts/AuthContext'

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean, error: any }> {
  constructor(props: any) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: any) {
    return { hasError: true, error }
  }
  componentDidCatch(error: any, errorInfo: any) {
    // You can log errorInfo here
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-red-50">
          <div className="bg-white p-8 rounded shadow text-center">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Frontend Error</h1>
            <pre className="text-sm text-gray-700 mb-4">{String(this.state.error)}</pre>
            <button onClick={() => window.location.reload()} className="bg-blue-600 text-white px-4 py-2 rounded">Reload</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <div className="min-h-screen bg-gray-50">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="piles" element={<Piles />} />
              <Route path="system" element={<System />} />
              <Route path="updates" element={<Updates />} />
              <Route path="browse" element={<Browse />} />
              <Route path="zim-viewer/:filePath" element={<ZimViewer />} />
            </Route>
          </Routes>
        </div>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App 