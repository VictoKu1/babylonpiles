import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react'
import { loginSession, logoutSession, readSession, SessionUser } from '../api/auth'
import { monitorSessionRequests } from '../api/session'

interface AuthContextType {
  user: SessionUser | null
  loading: boolean
  isAuthenticated: boolean
  sessionExpired: boolean
  login: (username: string, password: string) => Promise<SessionUser>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [sessionExpired, setSessionExpired] = useState(false)
  const currentUser = useRef<SessionUser | null>(null)
  const sessionVersion = useRef(0)

  useEffect(() => {
    let cancelled = false
    const stopMonitoring = monitorSessionRequests(window.location.origin, () => sessionVersion.current, () => {
      if (!currentUser.current) return
      sessionVersion.current += 1
      currentUser.current = null
      setUser(null)
      setSessionExpired(true)
    })
    const version = sessionVersion.current
    readSession()
      .then(verifiedUser => {
        if (!cancelled && version === sessionVersion.current) {
          currentUser.current = verifiedUser
          setUser(verifiedUser)
        }
      })
      .catch(() => {
        if (!cancelled && version === sessionVersion.current) {
          currentUser.current = null
          setUser(null)
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true; stopMonitoring() }
  }, [])

  const login = async (username: string, password: string) => {
    const verifiedUser = await loginSession(username, password)
    sessionVersion.current += 1
    currentUser.current = verifiedUser
    setUser(verifiedUser)
    setSessionExpired(false)
    return verifiedUser
  }

  const logout = async () => {
    await logoutSession()
    sessionVersion.current += 1
    currentUser.current = null
    setUser(null)
    setSessionExpired(false)
  }

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: user !== null, sessionExpired, login, logout }}>
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
