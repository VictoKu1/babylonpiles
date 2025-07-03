import React from 'react'

export function Updates() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Updates</h1>
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <p className="text-gray-500">No updates available.</p>
          <button className="mt-4 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
            Check for Updates
          </button>
        </div>
      </div>
    </div>
  )
} 