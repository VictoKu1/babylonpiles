import React from 'react'
import { NavLink } from 'react-router-dom'

export function Sidebar() {
  return (
    <aside className="w-64 bg-white shadow-sm">
      <nav className="mt-5 px-2">
        <NavLink
          to="/"
          className={({ isActive }) =>
            `group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
              isActive
                ? 'bg-gray-100 text-gray-900'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          Dashboard
        </NavLink>
        <NavLink
          to="/piles"
          className={({ isActive }) =>
            `group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
              isActive
                ? 'bg-gray-100 text-gray-900'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          Piles
        </NavLink>
        <NavLink
          to="/system"
          className={({ isActive }) =>
            `group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
              isActive
                ? 'bg-gray-100 text-gray-900'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          System
        </NavLink>
        <NavLink
          to="/updates"
          className={({ isActive }) =>
            `group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
              isActive
                ? 'bg-gray-100 text-gray-900'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          Updates
        </NavLink>
      </nav>
    </aside>
  )
} 