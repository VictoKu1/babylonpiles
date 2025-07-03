import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Piles } from './pages/Piles'
import { System } from './pages/System'
import { Updates } from './pages/Updates'
import { Login } from './pages/Login'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-gray-50">
        <h1 className="text-2xl font-bold text-center py-8">BabylonPiles</h1>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="piles" element={<Piles />} />
            <Route path="system" element={<System />} />
            <Route path="updates" element={<Updates />} />
          </Route>
        </Routes>
      </div>
    </AuthProvider>
  )
}

export default App 