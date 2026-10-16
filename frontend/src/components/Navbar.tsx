import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Navbar() {
  const { user, logout } = useAuth()
  const [signingOut, setSigningOut] = useState(false)
  const [error, setError] = useState('')

  const handleLogout = async () => {
    setSigningOut(true)
    setError('')
    try {
      await logout()
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to sign out. Please try again.')
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-xl font-bold text-gray-900">
              BabylonPiles
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">{user?.username}</span>
            <Link to="/browse" className="hover:text-blue-600">Browse Files</Link>
            <button type="button" onClick={handleLogout} disabled={signingOut} className="text-sm text-blue-700 hover:underline disabled:opacity-50">{signingOut ? 'Signing out...' : 'Sign out'}</button>
          </div>
        </div>
        {error && <p role="alert" className="pb-3 text-sm text-red-700">{error}</p>}
      </div>
    </nav>
  )
}
