import * as React from 'react';
import { NavLink } from 'react-router-dom'

interface SystemInfo {
  version: string;
  build: string;
  status: string;
  mode: string;
}

export function Sidebar() {
  const [systemInfo, setSystemInfo] = React.useState<SystemInfo>({
    version: "1.0.0",
    build: "2024.01.15",
    status: "Loading...",
    mode: "Loading..."
  });
  const [showSoftwareInfo, setShowSoftwareInfo] = React.useState(false);

  React.useEffect(() => {
    const fetchSystemInfo = async () => {
      let version = "1.0.0";
      let build = "2024.01.15";
      try {
        // Try to get git info from backend
        const gitResp = await fetch('http://localhost:8080/api/v1/system/gitinfo');
        if (gitResp.ok) {
          const gitData = await gitResp.json();
          if (gitData.version) version = gitData.version;
          if (gitData.build) build = gitData.build;
        }
      } catch (e) {
        // Ignore, fallback to defaults
      }
      try {
        const response = await fetch('http://localhost:8080/api/v1/system/status');
        if (response.ok) {
          const data = await response.json();
          setSystemInfo({
            version,
            build,
            status: data.system_status === "online" ? "Online" : "Offline",
            mode: data.mode === "learn" ? "Learn" : "Store"
          });
        }
      } catch (error) {
        console.error('Error fetching system info:', error);
        setSystemInfo({
          version,
          build,
          status: "Offline",
          mode: "Unknown"
        });
      }
    };

    fetchSystemInfo();
    // Refresh system info every 30 seconds
    const interval = setInterval(fetchSystemInfo, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="w-64 bg-white shadow-sm flex flex-col h-full">
      <nav className="mt-5 px-2 flex-1">
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
      <div className="border-t border-gray-200 px-4 py-3 bg-gray-50">
        <button
          className="group flex items-center px-2 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900 w-full text-left transition-colors"
          style={{ outline: 'none', border: 'none', background: 'none' }}
          onClick={() => setShowSoftwareInfo(true)}
        >
          Software Information
        </button>
      </div>
      {showSoftwareInfo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-xs w-full mx-4 shadow-lg">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">Software Information</h2>
              <button
                onClick={() => setShowSoftwareInfo(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="text-xs text-gray-700 space-y-2">
              <div className="flex justify-between">
                <span>Version:</span>
                <span className="font-mono">{systemInfo.version}</span>
              </div>
              <div className="flex justify-between">
                <span>Build:</span>
                <span className="font-mono">{systemInfo.build}</span>
              </div>
              <div className="flex justify-between">
                <span>Status:</span>
                <span className={`font-medium ${systemInfo.status === "Online" ? "text-green-600" : "text-red-600"}`}>{systemInfo.status}</span>
              </div>
              <div className="flex justify-between">
                <span>Mode:</span>
                <span className={`font-medium ${systemInfo.mode === "Learn" ? "text-blue-600" : "text-orange-600"}`}>{systemInfo.mode}</span>
              </div>
            </div>
            <div className="pt-2 border-t border-gray-200 mt-2">
              <a 
                href="https://github.com/VictoKu1/babylonpiles" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center justify-center text-xs text-blue-600 hover:text-blue-800 font-medium mt-2"
              >
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 0C4.477 0 0 4.484 0 10.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0110 4.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.203 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.942.359.31.678.921.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0020 10.017C20 4.484 15.522 0 10 0z" clipRule="evenodd" />
                </svg>
                GitHub Repository
              </a>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
} 