import React, { useState, useEffect } from 'react'

interface DashboardData {
  totalPiles: number
  storageUsed: string
  systemStatus: string
  lastUpdate: string
  storageDetails: {
    total: string
    used: string
    free: string
    percent: number
  }
  systemMode: string
  internetAvailable: boolean
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData>({
    totalPiles: 0,
    storageUsed: '0 GB',
    systemStatus: 'Loading...',
    lastUpdate: 'Never',
    storageDetails: {
      total: '0 GB',
      used: '0 GB',
      free: '0 GB',
      percent: 0
    },
    systemMode: 'store',
    internetAvailable: false
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string): string => {
    if (!dateString || dateString === 'Never') return 'Never'
    try {
      const date = new Date(dateString)
      return date.toLocaleString()
    } catch {
      return 'Invalid Date'
    }
  }

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch piles count
      const pilesResponse = await fetch('http://localhost:8080/api/v1/piles/')
      const pilesData = pilesResponse.ok ? await pilesResponse.json() : { total: 0 }

      // Fetch system status
      const statusResponse = await fetch('http://localhost:8080/api/v1/system/status')
      const statusData = statusResponse.ok ? await statusResponse.json() : { data: {} }

      // Fetch storage info
      const storageResponse = await fetch('http://localhost:8080/api/v1/system/storage')
      const storageData = storageResponse.ok ? await storageResponse.json() : { data: {} }

      // Fetch system mode
      const modeResponse = await fetch('http://localhost:8080/api/v1/system/mode')
      const modeData = modeResponse.ok ? await modeResponse.json() : { data: { current_mode: 'store' } }

      // Calculate storage used
      const storageInfo = storageData.data || {}
      const usedBytes = storageInfo.used_bytes || 0
      const totalBytes = storageInfo.total_bytes || 0
      const freeBytes = storageInfo.free_bytes || 0
      const percentUsed = totalBytes > 0 ? Math.round((usedBytes / totalBytes) * 100) : 0

      // Get system status info
      const systemInfo = statusData.data || {}
      const lastUpdate = systemInfo.last_update || 'Never'
      const internetAvailable = systemInfo.internet_available || false
      const currentMode = modeData.data?.current_mode || 'store'

      setData({
        totalPiles: pilesData.total || 0,
        storageUsed: formatBytes(usedBytes),
        systemStatus: currentMode === 'learn' ? 'Learn Mode' : 'Store Mode',
        lastUpdate: formatDate(lastUpdate),
        storageDetails: {
          total: formatBytes(totalBytes),
          used: formatBytes(usedBytes),
          free: formatBytes(freeBytes),
          percent: percentUsed
        },
        systemMode: currentMode,
        internetAvailable
      })

    } catch (err) {
      console.error('Error loading dashboard data:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboardData()
    
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (mode: string) => {
    return mode === 'learn' ? 'text-green-600' : 'text-yellow-600'
  }

  const getStorageColor = (percent: number) => {
    if (percent < 50) return 'text-green-600'
    if (percent < 80) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-lg shadow animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
          <button 
            onClick={loadDashboardData}
            className="mt-2 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <button
          onClick={loadDashboardData}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Total Piles</h3>
          <p className="text-3xl font-bold text-blue-600">{data.totalPiles}</p>
          <p className="text-sm text-gray-500 mt-1">Content sources</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Storage Used</h3>
          <p className={`text-3xl font-bold ${getStorageColor(data.storageDetails.percent)}`}>
            {data.storageUsed}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {data.storageDetails.percent}% of {data.storageDetails.total}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          <p className={`text-3xl font-bold ${getStatusColor(data.systemMode)}`}>
            {data.systemStatus}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Internet: {data.internetAvailable ? 'Available' : 'Offline'}
          </p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Last Update</h3>
          <p className="text-3xl font-bold text-gray-600">
            {data.lastUpdate === 'Never' ? 'Never' : 'Updated'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {data.lastUpdate}
          </p>
        </div>
      </div>

      {/* Storage Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Storage Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-sm text-gray-500">Total Storage</p>
            <p className="text-lg font-semibold">{data.storageDetails.total}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Used Storage</p>
            <p className="text-lg font-semibold">{data.storageDetails.used}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Free Storage</p>
            <p className="text-lg font-semibold">{data.storageDetails.free}</p>
          </div>
        </div>
        
        {/* Storage Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Storage Usage</span>
            <span>{data.storageDetails.percent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-300 ${
                data.storageDetails.percent < 50 ? 'bg-green-500' :
                data.storageDetails.percent < 80 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${data.storageDetails.percent}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  )
} 