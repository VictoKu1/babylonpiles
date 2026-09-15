import React from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { isAdminUser } from '../api/auth'

export function RequireAdmin() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <div role="status" className="min-h-screen flex items-center justify-center text-gray-600">Checking session...</div>
  }
  if (!isAdminUser(user)) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <Outlet />
}
