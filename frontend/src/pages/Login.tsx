import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { isAdminUser } from '../api/auth'

export function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { user, loading, login, logout } = useAuth()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const location = useLocation()
  const requestedPath = location.state?.from
  const destination = typeof requestedPath === 'string' && requestedPath.startsWith('/') &&
    !requestedPath.startsWith('//') && !requestedPath.includes('\\') && requestedPath !== '/login'
    ? requestedPath : '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await login(username, password)
      setPassword('')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Sign in failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!loading && isAdminUser(user)) return <Navigate to={destination} replace />

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to BabylonPiles
          </h2>
          <p className="mt-3 text-center text-sm text-gray-600">Use an administrator account created by the server operator.</p>
        </div>
        {error && <p role="alert" className="text-red-700 text-sm">{error}</p>}
        {user && !isAdminUser(user) && (
          <div role="alert" className="text-sm text-amber-800 bg-amber-50 p-4 rounded">
            <p>This account does not have administrator access. Public content is available from the hotspot page.</p>
            <button type="button" className="mt-2 underline" onClick={() => logout().catch(error => setError(error.message))}>Sign out of this account</button>
          </div>
        )}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <input
                type="text"
                name="username"
                autoComplete="username"
                aria-label="Username"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div>
              <input
                type="password"
                name="password"
                autoComplete="current-password"
                aria-label="Password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading || submitting}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Checking session...' : submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
        <p className="text-center text-sm"><Link to="/hotspot" className="text-blue-700 hover:underline">Browse public hotspot content</Link></p>
      </div>
    </div>
  )
}
