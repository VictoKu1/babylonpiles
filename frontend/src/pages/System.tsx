import React from 'react'

export function System() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">System</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Status</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Mode:</span>
              <span className="font-medium">Store</span>
            </div>
            <div className="flex justify-between">
              <span>CPU Usage:</span>
              <span className="font-medium">0%</span>
            </div>
            <div className="flex justify-between">
              <span>Memory Usage:</span>
              <span className="font-medium">0%</span>
            </div>
            <div className="flex justify-between">
              <span>Disk Usage:</span>
              <span className="font-medium">0%</span>
            </div>
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Network</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="font-medium text-green-600">Online</span>
            </div>
            <div className="flex justify-between">
              <span>IP Address:</span>
              <span className="font-medium">192.168.1.100</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 