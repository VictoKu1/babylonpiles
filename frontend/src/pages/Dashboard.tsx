import React, { useState, useEffect } from "react";

interface Pile {
  id: number;
  name: string;
  display_name: string;
  description: string;
  category: string;
  source_type: string;
  file_path?: string;
  file_size?: number;
  is_downloading?: boolean;
  download_progress?: number;
  created_at?: string;
}

interface DashboardData {
  totalPiles: number;
  downloadedPiles: number;
  downloadingPiles: number;
  storageUsed: string;
  systemStatus: string;
  lastUpdate: string;
  storageDetails: {
    total: string;
    used: string;
    free: string;
    percent: number;
  };
  systemMode: string;
  internetAvailable: boolean;
  recentPiles: Pile[];
}

export function Dashboard() {
  const [data, setData] = useState<DashboardData>({
    totalPiles: 0,
    downloadedPiles: 0,
    downloadingPiles: 0,
    storageUsed: "0 GB",
    systemStatus: "Loading...",
    lastUpdate: "Never",
    storageDetails: {
      total: "0 GB",
      used: "0 GB",
      free: "0 GB",
      percent: 0,
    },
    systemMode: "store",
    internetAvailable: false,
    recentPiles: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    if (!dateString || dateString === "Never") return "Never";
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return "Invalid Date";
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch piles with detailed information
      const pilesResponse = await fetch("http://localhost:8080/api/v1/piles/");
      const pilesData = pilesResponse.ok
        ? await pilesResponse.json()
        : { total: 0, data: [] };

      // Calculate pile statistics
      const piles = pilesData.data || [];
      const downloadedPiles = piles.filter(
        (pile: Pile) => pile.file_path
      ).length;
      const downloadingPiles = piles.filter(
        (pile: Pile) => pile.is_downloading
      ).length;

      // Get recent downloaded piles (last 5)
      const recentPiles = piles
        .filter((pile: Pile) => pile.file_path)
        .sort((a: Pile, b: Pile) => {
          const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
          const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
          return dateB - dateA;
        })
        .slice(0, 5);

      // Fetch system status
      const statusResponse = await fetch(
        "http://localhost:8080/api/v1/system/status"
      );
      const statusData = statusResponse.ok
        ? await statusResponse.json()
        : { data: {} };

      // Fetch system mode
      const modeResponse = await fetch(
        "http://localhost:8080/api/v1/system/mode"
      );
      const modeData = modeResponse.ok
        ? await modeResponse.json()
        : { data: { current_mode: "store" } };

      // Fetch system metrics for disk usage
      const metricsResponse = await fetch(
        "http://localhost:8080/api/v1/system/metrics"
      );
      const metricsData = metricsResponse.ok
        ? await metricsResponse.json()
        : { data: { disk: { total_bytes: 0, used_bytes: 0, free_bytes: 0 } } };

      // Calculate storage used by downloaded piles
      const downloadedPilesSize = piles
        .filter((pile: Pile) => pile.file_path && pile.file_size)
        .reduce(
          (total: number, pile: Pile) => total + (pile.file_size || 0),
          0
        );

      // Get disk usage from system metrics
      const diskInfo = metricsData.data?.disk || {};
      const totalDiskBytes = diskInfo.total_bytes || 0;
      const usedDiskBytes = diskInfo.used_bytes || 0;
      const freeDiskBytes = diskInfo.free_bytes || 0;

      // Calculate percentage based on actual disk usage
      const percentUsed =
        totalDiskBytes > 0 ? (usedDiskBytes / totalDiskBytes) * 100 : 0;

      // Get system status info
      const systemInfo = statusData.data || {};
      const lastUpdate = systemInfo.last_update || "Never";
      const internetAvailable = systemInfo.internet_available || false;
      const currentMode = modeData.data?.current_mode || "store";

      setData({
        totalPiles: pilesData.total || 0,
        downloadedPiles,
        downloadingPiles,
        storageUsed: formatBytes(downloadedPilesSize),
        systemStatus: currentMode === "learn" ? "Learn Mode" : "Store Mode",
        lastUpdate: formatDate(lastUpdate),
        storageDetails: {
          total: formatBytes(totalDiskBytes),
          used: formatBytes(usedDiskBytes),
          free: formatBytes(freeDiskBytes),
          percent: percentUsed,
        },
        systemMode: currentMode,
        internetAvailable,
        recentPiles,
      });
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();

    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (mode: string) => {
    return mode === "learn" ? "text-green-600" : "text-yellow-600";
  };

  const getStorageColor = (percent: number) => {
    if (percent < 50) return "text-green-600";
    if (percent < 80) return "text-yellow-600";
    return "text-red-600";
  };

  if (loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-white p-6 rounded-lg shadow animate-pulse"
            >
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-8 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    );
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
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex space-x-3">
          <button
            onClick={loadDashboardData}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Total Piles</h3>
          <p className="text-3xl font-bold text-blue-600">{data.totalPiles}</p>
          <p className="text-sm text-gray-500 mt-1">Content sources</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Downloaded</h3>
          <p className="text-3xl font-bold text-green-600">
            {data.downloadedPiles}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {data.downloadedPiles > 0
              ? `${Math.round(
                  (data.downloadedPiles / data.totalPiles) * 100
                )}% of total`
              : "No content downloaded"}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">Downloading</h3>
          <p className="text-3xl font-bold text-yellow-600">
            {data.downloadingPiles}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {data.downloadingPiles > 0 ? "In progress" : "No active downloads"}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900">System Status</h3>
          <p
            className={`text-3xl font-bold ${getStatusColor(data.systemMode)}`}
          >
            {data.systemStatus}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Internet: {data.internetAvailable ? "Available" : "Offline"}
          </p>
        </div>
      </div>

      {/* Recent Downloads Section */}
      {data.recentPiles.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Recently Downloaded
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.recentPiles.map((pile) => (
              <div
                key={pile.id}
                className="border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 text-sm">
                      {pile.display_name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {pile.category}
                    </p>
                    {pile.file_size && (
                      <p className="text-xs text-gray-600 mt-1">
                        {formatBytes(pile.file_size)}
                      </p>
                    )}
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      pile.source_type === "kiwix"
                        ? "bg-blue-100 text-blue-800"
                        : pile.source_type === "http"
                        ? "bg-green-100 text-green-800"
                        : "bg-purple-100 text-purple-800"
                    }`}
                  >
                    {pile.source_type.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Storage Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">Disk Storage</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-500">Total Disk</p>
            <p className="text-lg font-semibold">{data.storageDetails.total}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Used Disk</p>
            <p className="text-lg font-semibold">{data.storageDetails.used}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Free Disk</p>
            <p className="text-lg font-semibold">{data.storageDetails.free}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Content Used</p>
            <p className="text-lg font-semibold">{data.storageUsed}</p>
          </div>
        </div>

        {/* Storage Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Disk Usage</span>
            <span>{Math.round(data.storageDetails.percent)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                data.storageDetails.percent < 50
                  ? "bg-green-500"
                  : data.storageDetails.percent < 80
                  ? "bg-yellow-500"
                  : "bg-red-500"
              }`}
              style={{ width: `${data.storageDetails.percent}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Content files use {data.storageUsed} of available disk space
          </p>
        </div>
      </div>
    </div>
  );
}
