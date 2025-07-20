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
  currentlyDownloading: {
    id: number;
    name: string;
    display_name: string;
    progress: number;
  }[];
  hotspotStatus: {
    is_running: boolean;
    ssid: string;
    password: string;
    ip_range: string;
    started_at: string | null;
    connected_devices: Array<{
      mac: string;
      ip: string;
      hostname: string;
      connected_at: string;
    }>;
    pending_requests: Array<{
      id: string;
      filename: string;
      editor_name: string;
      client_ip: string;
      client_mac: string;
      requested_at: string;
      status: string;
    }>;
    user_config: {
      user_name: string;
      hotspot_name: string;
    };
  };
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
    currentlyDownloading: [],
    hotspotStatus: {
      is_running: false,
      ssid: "",
      password: "",
      ip_range: "",
      started_at: null,
      connected_devices: [],
      pending_requests: [],
      user_config: {
        user_name: "",
        hotspot_name: "",
      },
    },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hotspotLoading, setHotspotLoading] = useState(false);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<any>(null);
  const [showRequirements, setShowRequirements] = useState(false);
  const [requirements, setRequirements] = useState<any>(null);
  const [showUserNameModal, setShowUserNameModal] = useState(false);
  const [userName, setUserName] = useState("");
  const [userNameLoading, setUserNameLoading] = useState(false);

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

  const handleStartHotspot = async () => {
    setHotspotLoading(true);
    try {
      const response = await fetch("http://localhost:8080/api/v1/system/hotspot/start", {
        method: "POST",
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Hotspot started: ${result.message}`);
        loadDashboardData(); // Refresh data
      } else {
        const errorData = await response.json();
        alert(`Failed to start hotspot: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error starting hotspot:", error);
      alert("Error starting hotspot");
    } finally {
      setHotspotLoading(false);
    }
  };

  const handleStopHotspot = async () => {
    setHotspotLoading(true);
    try {
      const response = await fetch("http://localhost:8080/api/v1/system/hotspot/stop", {
        method: "POST",
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Hotspot stopped: ${result.message}`);
        loadDashboardData(); // Refresh data
      } else {
        const errorData = await response.json();
        alert(`Failed to stop hotspot: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error stopping hotspot:", error);
      alert("Error stopping hotspot");
    } finally {
      setHotspotLoading(false);
    }
  };

  const handleApproveRequest = async (requestId: string) => {
    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/system/hotspot/approve-request/${requestId}`,
        {
          method: "POST",
        }
      );

      if (response.ok) {
        const result = await response.json();
        alert(`Request approved: ${result.message}`);
        setShowRequestModal(false);
        loadDashboardData(); // Refresh data
      } else {
        const errorData = await response.json();
        alert(`Failed to approve request: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error approving request:", error);
      alert("Error approving request");
    }
  };

  const handleRejectRequest = async (requestId: string, reason: string = "") => {
    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/system/hotspot/reject-request/${requestId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ reason }),
        }
      );

      if (response.ok) {
        const result = await response.json();
        alert(`Request rejected: ${result.message}`);
        setShowRequestModal(false);
        loadDashboardData(); // Refresh data
      } else {
        const errorData = await response.json();
        alert(`Failed to reject request: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error rejecting request:", error);
      alert("Error rejecting request");
    }
  };

  const checkHotspotRequirements = async () => {
    try {
      const response = await fetch("http://localhost:8080/api/v1/system/hotspot/requirements");
      
      if (response.ok) {
        const result = await response.json();
        setRequirements(result.data);
        setShowRequirements(true);
      } else {
        const errorData = await response.json();
        alert(`Failed to get requirements: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error getting requirements:", error);
      alert("Error getting system requirements");
    }
  };

  const handleUpdateUserName = async () => {
    if (!userName.trim()) {
      alert("Please enter a user name");
      return;
    }

    setUserNameLoading(true);
    try {
      const response = await fetch("http://localhost:8080/api/v1/system/user/config", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_name: userName.trim() }),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`User name updated: ${result.message}`);
        setShowUserNameModal(false);
        setUserName("");
        loadDashboardData(); // Refresh data to get updated hotspot name
      } else {
        const errorData = await response.json();
        alert(`Failed to update user name: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error updating user name:", error);
      alert("Error updating user name");
    } finally {
      setUserNameLoading(false);
    }
  };

  const getUserDisplayName = () => {
    return data.hotspotStatus.user_config?.user_name || "BabylonPiles";
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

      // Get currently downloading piles for display
      const currentlyDownloading = piles
        .filter((pile: Pile) => pile.is_downloading)
        .map((pile: Pile) => ({
          ...pile,
          progress: pile.download_progress || 0
        }));

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

      // Fetch files to calculate content storage
      const filesResponse = await fetch("http://localhost:8080/api/v1/files?path=");
      const filesData = filesResponse.ok
        ? await filesResponse.json()
        : { items: [] };

      // Calculate storage used by downloaded piles
      const downloadedPilesSize = piles
        .filter((pile: Pile) => pile.file_path && pile.file_size)
        .reduce(
          (total: number, pile: Pile) => total + (pile.file_size || 0),
          0
        );

      // Calculate content storage (files + piles)
      const files = filesData.items || [];
      const filesSize = files
        .filter((file: any) => !file.is_dir && file.size)
        .reduce((total: number, file: any) => total + (file.size || 0), 0);

      // Total content storage = files + downloaded piles
      const totalContentStorage = filesSize + downloadedPilesSize;

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

      // Fetch hotspot status
      const hotspotResponse = await fetch(
        "http://localhost:8080/api/v1/system/hotspot/status"
      );
      const hotspotData = hotspotResponse.ok
        ? await hotspotResponse.json()
        : { data: {} };

      setData({
        totalPiles: pilesData.total || 0,
        downloadedPiles,
        downloadingPiles,
        storageUsed: formatBytes(totalContentStorage), // Use content storage instead of disk usage
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
        currentlyDownloading, // Add this to the interface
        hotspotStatus: hotspotData.data || {
          is_running: false,
          ssid: "",
          password: "",
          ip_range: "",
          started_at: null,
          connected_devices: [],
          pending_requests: [],
          user_config: {
            user_name: "",
            hotspot_name: "",
          },
        },
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
        <div className="flex items-center space-x-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{getUserDisplayName()}</h1>
            <p className="text-gray-600">Content Management Dashboard</p>
          </div>
          <button
            onClick={() => setShowUserNameModal(true)}
            className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700"
            title="Configure user name"
          >
            ⚙️
          </button>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadDashboardData}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
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
          <h3 className="text-lg font-medium text-gray-900">Content Storage</h3>
          <p className="text-3xl font-bold text-purple-600">
            {data.storageUsed}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {data.downloadedPiles > 0 
              ? `${data.downloadedPiles} files downloaded`
              : "No content downloaded"
            }
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

      {/* WiFi Hotspot Section */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-medium text-gray-900">WiFi Hotspot</h2>
          <div className="flex space-x-2">
            <button
              onClick={checkHotspotRequirements}
              className="bg-blue-600 text-white px-3 py-2 rounded text-sm hover:bg-blue-700"
            >
              System Requirements
            </button>
            {!data.hotspotStatus.is_running ? (
              <button
                onClick={handleStartHotspot}
                disabled={hotspotLoading}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
              >
                {hotspotLoading ? "Starting..." : "Start Hotspot"}
              </button>
            ) : (
              <button
                onClick={handleStopHotspot}
                disabled={hotspotLoading}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
              >
                {hotspotLoading ? "Stopping..." : "Stop Hotspot"}
              </button>
            )}
          </div>
        </div>

        {data.hotspotStatus.is_running ? (
          <div className="space-y-4">
            {/* Hotspot Info */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <h3 className="font-semibold text-green-900 mb-2">Hotspot Information</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="font-medium text-green-700">SSID:</span>
                  <p className="text-green-900 font-mono">{data.hotspotStatus.ssid}</p>
                </div>
                <div>
                  <span className="font-medium text-green-700">Password:</span>
                  <p className="text-green-900 font-mono">{data.hotspotStatus.password}</p>
                </div>
                <div>
                  <span className="font-medium text-green-700">IP Range:</span>
                  <p className="text-green-900 font-mono">{data.hotspotStatus.ip_range}</p>
                </div>
                <div>
                  <span className="font-medium text-green-700">Started:</span>
                  <p className="text-green-900">{formatDate(data.hotspotStatus.started_at || "")}</p>
                </div>
              </div>
            </div>

            {/* Connected Devices */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">
                Connected Devices ({data.hotspotStatus.connected_devices.length})
              </h3>
              {data.hotspotStatus.connected_devices.length > 0 ? (
                <div className="space-y-2">
                  {data.hotspotStatus.connected_devices.map((device, index) => (
                    <div key={index} className="flex justify-between items-center text-sm">
                      <div>
                        <span className="font-medium text-blue-700">Device:</span>
                        <span className="text-blue-900 ml-2">{device.hostname}</span>
                      </div>
                      <div>
                        <span className="font-medium text-blue-700">IP:</span>
                        <span className="text-blue-900 ml-2 font-mono">{device.ip}</span>
                      </div>
                      <div>
                        <span className="font-medium text-blue-700">MAC:</span>
                        <span className="text-blue-900 ml-2 font-mono">{device.mac}</span>
                      </div>
                      <div>
                        <span className="font-medium text-blue-700">Connected:</span>
                        <span className="text-blue-900 ml-2">{formatDate(device.connected_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-blue-700 text-sm">No devices connected</p>
              )}
            </div>

            {/* Pending Requests */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <h3 className="font-semibold text-yellow-900 mb-2">
                Pending Upload Requests ({data.hotspotStatus.pending_requests.filter(r => r.status === "pending").length})
              </h3>
              {data.hotspotStatus.pending_requests.filter(r => r.status === "pending").length > 0 ? (
                <div className="space-y-2">
                  {data.hotspotStatus.pending_requests
                    .filter(r => r.status === "pending")
                    .map((request) => (
                      <div key={request.id} className="border border-yellow-300 rounded p-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <p className="font-medium text-yellow-900">File: {request.filename}</p>
                            <p className="text-sm text-yellow-700">Editor: {request.editor_name}</p>
                            <p className="text-sm text-yellow-700">IP: {request.client_ip || "Unknown"}</p>
                            <p className="text-sm text-yellow-700">MAC: {request.client_mac || "Unknown"}</p>
                            <p className="text-sm text-yellow-700">Requested: {formatDate(request.requested_at)}</p>
                          </div>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleApproveRequest(request.id)}
                              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setSelectedRequest(request);
                                setShowRequestModal(true);
                              }}
                              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700"
                            >
                              Reject
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-yellow-700 text-sm">No pending requests</p>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p className="mb-2">WiFi hotspot is not running</p>
            <p className="text-sm">Start the hotspot to allow devices to connect and access public content</p>
          </div>
        )}
      </div>

      {/* Currently Downloading Section */}
      {data.currentlyDownloading.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Currently Downloading
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.currentlyDownloading.map((pile) => (
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
                      {pile.name}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      Progress: {pile.progress}%
                    </p>
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
          <h2 className="text-lg font-medium text-gray-900">Content Storage</h2>
        </div>
        
        {/* Content Storage Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-500">Content Used</p>
            <p className="text-lg font-semibold">{data.storageUsed}</p>
            <p className="text-xs text-gray-500 mt-1">
              {data.downloadedPiles > 0 
                ? `${data.downloadedPiles} downloaded files`
                : "No content downloaded yet"
              }
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Available Space</p>
            <p className="text-lg font-semibold">{data.storageDetails.free}</p>
            <p className="text-xs text-gray-500 mt-1">
              Free disk space for content
            </p>
          </div>
        </div>

        {/* Content Storage Progress Bar */}
        {data.downloadedPiles > 0 && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Content Storage</span>
              <span>
                {data.storageUsed} of {data.storageDetails.total}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ 
                  width: `${Math.min(
                    (parseInt(data.storageUsed.replace(/[^\d]/g, '')) / 
                    parseInt(data.storageDetails.total.replace(/[^\d]/g, ''))) * 100, 
                    100
                  )}%` 
                }}
              ></div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Content files using {data.storageUsed} of available disk space
            </p>
          </div>
        )}

        {/* System Disk Info (Collapsible) */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <details className="group">
            <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-800">
              System Disk Information
            </summary>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500">Total Disk</p>
                <p className="text-sm font-semibold">{data.storageDetails.total}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Used Disk</p>
                <p className="text-sm font-semibold">{data.storageDetails.used}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Free Disk</p>
                <p className="text-sm font-semibold">{data.storageDetails.free}</p>
              </div>
            </div>
            
            {/* System Disk Progress Bar */}
            <div className="mt-3">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>System Disk Usage</span>
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
            </div>
          </details>
        </div>
      </div>

      {/* Reject Request Modal */}
      {showRequestModal && selectedRequest && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-bold mb-4">Reject Upload Request</h3>
            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                <strong>File:</strong> {selectedRequest.filename}
              </p>
              <p className="text-sm text-gray-600 mb-2">
                <strong>Editor:</strong> {selectedRequest.editor_name}
              </p>
              <p className="text-sm text-gray-600 mb-4">
                <strong>Requested:</strong> {formatDate(selectedRequest.requested_at)}
              </p>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rejection Reason (optional):
              </label>
              <textarea
                id="rejection-reason"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Enter reason for rejection..."
              />
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowRequestModal(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const reason = (document.getElementById("rejection-reason") as HTMLTextAreaElement)?.value || "";
                  handleRejectRequest(selectedRequest.id, reason);
                }}
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
              >
                Reject Request
              </button>
            </div>
          </div>
        </div>
      )}

      {/* System Requirements Modal */}
      {showRequirements && requirements && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">System Requirements for WiFi Hotspot</h3>
              <button
                onClick={() => setShowRequirements(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-4">
              {/* System Information */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">System Information</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-blue-700">Platform:</span>
                    <p className="text-blue-900">{requirements.system_info.platform}</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-700">Machine:</span>
                    <p className="text-blue-900">{requirements.system_info.machine}</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-700">Processor:</span>
                    <p className="text-blue-900">{requirements.system_info.processor}</p>
                  </div>
                  <div>
                    <span className="font-medium text-blue-700">WiFi Interface:</span>
                    <p className="text-blue-900">{requirements.system_info.wifi_interface}</p>
                  </div>
                </div>
              </div>

              {/* Requirements Status */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-2">Requirements Status</h4>
                <div className="space-y-2">
                  <div className="flex items-center">
                    <span className={`w-4 h-4 rounded-full mr-2 ${requirements.requirements.hostapd ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    <span className="text-sm">hostapd: {requirements.requirements.hostapd ? '✅ Available' : '❌ Missing'}</span>
                  </div>
                  <div className="flex items-center">
                    <span className={`w-4 h-4 rounded-full mr-2 ${requirements.requirements.dnsmasq ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    <span className="text-sm">dnsmasq: {requirements.requirements.dnsmasq ? '✅ Available' : '❌ Missing'}</span>
                  </div>
                  <div className="flex items-center">
                    <span className={`w-4 h-4 rounded-full mr-2 ${requirements.requirements.wifi_interface ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    <span className="text-sm">WiFi Interface: {requirements.requirements.wifi_interface ? '✅ Available' : '❌ Missing'}</span>
                  </div>
                  <div className="flex items-center">
                    <span className={`w-4 h-4 rounded-full mr-2 ${requirements.requirements.root_privileges ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    <span className="text-sm">Root Privileges: {requirements.requirements.root_privileges ? '✅ Available' : '❌ Missing'}</span>
                  </div>
                </div>
              </div>

              {/* Installation Instructions */}
              {requirements.installation_instructions && Object.keys(requirements.installation_instructions).length > 0 && (
                <div className="bg-green-50 p-4 rounded-lg">
                  <h4 className="font-semibold text-green-900 mb-2">Installation Instructions</h4>
                  <div className="space-y-2 text-sm">
                    {Object.entries(requirements.installation_instructions).map(([package_name, command]) => (
                      <div key={package_name}>
                        <span className="font-medium text-green-700">{package_name}:</span>
                        <code className="block bg-green-100 p-2 rounded mt-1 text-green-900">{command}</code>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div className="bg-yellow-50 p-4 rounded-lg">
                <h4 className="font-semibold text-yellow-900 mb-2">Recommendations</h4>
                <div className="space-y-2 text-sm text-yellow-800">
                  {requirements.recommendations.raspberry_pi && (
                    <p>• {requirements.recommendations.raspberry_pi}</p>
                  )}
                  {requirements.recommendations.linux && (
                    <p>• {requirements.recommendations.linux}</p>
                  )}
                  {requirements.recommendations.other && (
                    <p>• {requirements.recommendations.other}</p>
                  )}
                </div>
              </div>

              {/* Hotspot Configuration */}
              <div className="bg-purple-50 p-4 rounded-lg">
                <h4 className="font-semibold text-purple-900 mb-2">Hotspot Configuration</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-purple-700">SSID:</span>
                    <p className="text-purple-900 font-mono">{requirements.hotspot_config.ssid}</p>
                  </div>
                  <div>
                    <span className="font-medium text-purple-700">IP Range:</span>
                    <p className="text-purple-900 font-mono">{requirements.hotspot_config.ip_range}</p>
                  </div>
                  <div>
                    <span className="font-medium text-purple-700">Gateway IP:</span>
                    <p className="text-purple-900 font-mono">{requirements.hotspot_config.gateway_ip}</p>
                  </div>
                  <div>
                    <span className="font-medium text-purple-700">Channel:</span>
                    <p className="text-purple-900 font-mono">{requirements.hotspot_config.channel}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowRequirements(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Close
              </button>
                         </div>
           </div>
         </div>
       )}

       {/* User Name Configuration Modal */}
       {showUserNameModal && (
         <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
           <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
             <h3 className="text-lg font-bold mb-4">Configure User Name</h3>
             <div className="mb-4">
               <p className="text-sm text-gray-600 mb-4">
                 Set your name to personalize the hotspot. The hotspot will be named "{userName || "YourName"}BabylonPiles".
               </p>
               <label className="block text-sm font-medium text-gray-700 mb-2">
                 Your Name:
               </label>
               <input
                 type="text"
                 value={userName}
                 onChange={(e) => setUserName(e.target.value)}
                 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                 placeholder="Enter your name..."
                 maxLength={20}
               />
               <p className="text-xs text-gray-500 mt-1">
                 Only letters and numbers allowed. Maximum 20 characters.
               </p>
             </div>
             <div className="flex justify-end space-x-3">
               <button
                 onClick={() => {
                   setShowUserNameModal(false);
                   setUserName("");
                 }}
                 className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
               >
                 Cancel
               </button>
               <button
                 onClick={handleUpdateUserName}
                 disabled={userNameLoading || !userName.trim()}
                 className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
               >
                 {userNameLoading ? "Updating..." : "Update Name"}
               </button>
             </div>
           </div>
         </div>
       )}
     </div>
   );
 }
