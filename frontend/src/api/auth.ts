export interface SessionUser {
  id: number
  username: string
  role: string
  is_active: boolean
  is_admin: boolean
}

export function isAdminUser(user: SessionUser | null): boolean {
  return user?.is_active === true && user.is_admin === true
}

function sessionUser(value: unknown): SessionUser {
  const user = value as SessionUser | undefined
  if (!user || typeof user.id !== 'number' || typeof user.username !== 'string' ||
      typeof user.role !== 'string' || typeof user.is_admin !== 'boolean' || user.is_active !== true) {
    throw new Error('The server did not return a valid active session.')
  }
  return user
}

export async function readSession(): Promise<SessionUser | null> {
  const response = await fetch('/api/v1/auth/me', { credentials: 'same-origin', cache: 'no-store' })
  if (response.status === 401 || response.status === 403) return null
  if (!response.ok) throw new Error('Unable to verify your session. Please sign in again.')
  const result = await response.json()
  if (result.success !== true) throw new Error('Unable to verify your session.')
  return sessionUser(result.data)
}

export async function loginSession(username: string, password: string): Promise<SessionUser> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) {
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After')?.trim() || ''
      const seconds = /^\d+$/.test(retryAfter) ? Number(retryAfter) : Math.ceil((Date.parse(retryAfter) - Date.now()) / 1000)
      const wait = Number.isFinite(seconds) && seconds > 0 && seconds <= 86400
        ? `in ${seconds} ${seconds === 1 ? 'second' : 'seconds'}` : 'shortly'
      throw new Error(`Too many sign-in attempts. Please try again ${wait}.`)
    }
    throw new Error(response.status === 401 ? 'Incorrect username or password.' : 'Sign in failed. Please try again.')
  }
  const result = await response.json()
  if (result.success !== true) throw new Error('Sign in failed. Please try again.')
  // The browser manages the HttpOnly cookie; never retain the response's bearer token.
  return sessionUser(result.data?.user)
}

export async function logoutSession(): Promise<void> {
  const response = await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin' })
  if (!response.ok) throw new Error('Unable to sign out. Please try again.')
}
