import React from 'react'

export function Piles() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Piles</h1>
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <p className="text-gray-500">No piles configured yet.</p>
          <button className="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Add Pile
          </button>
        </div>
      </div>
    </div>
  )
} 