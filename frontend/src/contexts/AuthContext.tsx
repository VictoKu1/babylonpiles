import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { loginSession, logoutSession, readSession, SessionUser } from '../api/auth'

interface AuthContextType {
  user: SessionUser | null
  loading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<SessionUser>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    readSession()
      .then(currentUser => { if (!cancelled) setUser(currentUser) })
      .catch(() => { if (!cancelled) setUser(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const login = async (username: string, password: string) => {
    const currentUser = await loginSession(username, password)
    setUser(currentUser)
    return currentUser
  }

  const logout = async () => {
    await logoutSession()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: user !== null, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
