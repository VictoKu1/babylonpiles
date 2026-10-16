import React, { useEffect, useState } from 'react'

interface SystemSnapshot {
  mode: string
  cpu: number | null
  memory: number | null
  disk: number | null
  internetAvailable: boolean
  addresses: string[]
}

export function System() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const responses = await Promise.all(['status', 'metrics', 'network'].map(endpoint =>
          fetch(`/api/v1/system/${endpoint}`, { signal: controller.signal })))
        if (responses.some(response => !response.ok)) throw new Error('Unable to load system information.')
        const [status, metrics, network] = await Promise.all(responses.map(response => response.json()))
        if (controller.signal.aborted) return
        const addresses = Object.values(network.data || {}).flatMap(value =>
          value && typeof value === 'object' && 'addresses' in value && Array.isArray(value.addresses)
            ? value.addresses.filter((address: unknown): address is string => typeof address === 'string') : [])
        setSnapshot({
          mode: status.data?.current_mode === 'learn' ? 'Learn' : status.data?.current_mode === 'store' ? 'Store' : 'Unknown',
          cpu: metrics.data?.cpu?.usage_percent ?? null,
          memory: metrics.data?.memory?.usage_percent ?? null,
          disk: metrics.data?.disk?.usage_percent ?? null,
          internetAvailable: status.data?.internet_available === true,
          addresses,
        })
        setError('')
      } catch {
        if (!controller.signal.aborted) setError('Unable to load system information.')
      }
    }
    void load()
    const interval = setInterval(() => void load(), 30000)
    return () => { controller.abort(); clearInterval(interval) }
  }, [refresh])

  const percent = (value: number | null | undefined) => value == null ? 'Unavailable' : `${value}%`
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">System</h1>
      {error && <div role="alert" className="mb-4 text-red-600">{error} <button onClick={() => setRefresh(value => value + 1)} className="underline">Retry</button></div>}
      {!snapshot && !error && <p>Loading system information...</p>}
      {snapshot && <>
      {error && <p className="mb-4 text-gray-500">Showing the last available readings.</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Status</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className="font-medium">{snapshot.mode}</span>
            </div>
            <div className="flex justify-between">
              <span>CPU Usage:</span>
              <span className="font-medium">{percent(snapshot.cpu)}</span>
            </div>
            <div className="flex justify-between">
              <span>Memory Usage:</span>
              <span className="font-medium">{percent(snapshot.memory)}</span>
            </div>
            <div className="flex justify-between">
              <span>Disk Usage:</span>
              <span className="font-medium">{percent(snapshot.disk)}</span>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Network</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Internet:</span>
              <span className="font-medium">{snapshot.internetAvailable ? 'Available' : 'Unavailable'}</span>
            </div>
            <div className="flex justify-between">
              <span>IP Addresses:</span>
              <span className="font-medium break-all">{snapshot.addresses.join(', ') || 'Unavailable'}</span>
            </div>
          </div>
        </div>
      </div>
      </>}
    </div>
  )
}
