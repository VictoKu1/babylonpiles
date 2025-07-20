import React, { useState, useEffect } from 'react';

interface PublicFile {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
  size_formatted: string;
  creator: string;
  created_at: string;
  download_url?: string;
}

interface UploadRequest {
  filename: string;
  editor_name: string;
  status: string;
  message: string;
}

export function HotspotClient() {
  const [files, setFiles] = useState<PublicFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploadRequest, setUploadRequest] = useState<UploadRequest | null>(null);
  const [formData, setFormData] = useState({
    filename: '',
    editor_name: ''
  });

  useEffect(() => {
    loadPublicContent();
  }, []);

  const loadPublicContent = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/system/hotspot/public-content');
      
      if (response.ok) {
        const data = await response.json();
        setFiles(data.data.files || []);
      } else {
        setError('Failed to load public content');
      }
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (file: PublicFile) => {
    if (!file.download_url) return;
    
    try {
      const response = await fetch(file.download_url);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Failed to download file');
      }
    } catch (err) {
      alert('Error downloading file');
    }
  };

  const handleUploadRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.filename || !formData.editor_name) {
      alert('Please fill in all fields');
      return;
    }

    try {
      const response = await fetch('/api/v1/system/hotspot/request-upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: formData.filename,
          editor_name: formData.editor_name,
          client_ip: '192.168.4.100', // Simplified for demo
          client_mac: '00:11:22:33:44:55' // Simplified for demo
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setUploadRequest(result.data);
        setShowUploadForm(false);
        setFormData({ filename: '', editor_name: '' });
      } else {
        const errorData = await response.json();
        alert(`Failed to submit request: ${errorData.detail}`);
      }
    } catch (err) {
      alert('Error submitting request');
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading public content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={loadPublicContent}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">BabylonPiles Hotspot</h1>
              <p className="text-sm text-gray-600">Public Content Access</p>
            </div>
            <button
              onClick={() => setShowUploadForm(true)}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              Request Upload
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload Request Status */}
        {uploadRequest && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-900 mb-2">Upload Request Status</h3>
            <p className="text-blue-700">
              <strong>File:</strong> {uploadRequest.filename}
            </p>
            <p className="text-blue-700">
              <strong>Editor:</strong> {uploadRequest.editor_name}
            </p>
            <p className="text-blue-700">
              <strong>Status:</strong> {uploadRequest.status}
            </p>
            <p className="text-blue-700">
              <strong>Message:</strong> {uploadRequest.message}
            </p>
            <button
              onClick={() => setUploadRequest(null)}
              className="mt-2 text-blue-600 hover:text-blue-800 text-sm"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Public Files */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">
              Public Content ({files.length} items)
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Browse and download public files and folders
            </p>
          </div>

          {files.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              <p>No public content available</p>
              <p className="text-sm mt-1">Contact the administrator to add public content</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Type
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Creator
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {files.map((file, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <span className="text-lg mr-2">
                            {file.is_dir ? '📁' : '📄'}
                          </span>
                          <span className="text-sm font-medium text-gray-900">
                            {file.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.is_dir ? 'Folder' : 'File'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.size_formatted}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.creator}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(file.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {!file.is_dir && file.download_url && (
                          <button
                            onClick={() => handleDownload(file)}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Download
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Upload Request Modal */}
      {showUploadForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-bold mb-4">Request Content Upload</h3>
            <form onSubmit={handleUploadRequest}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  File Name
                </label>
                <input
                  type="text"
                  value={formData.filename}
                  onChange={(e) => setFormData({ ...formData, filename: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter file name..."
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Name
                </label>
                <input
                  type="text"
                  value={formData.editor_name}
                  onChange={(e) => setFormData({ ...formData, editor_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter your name..."
                  required
                />
              </div>
              <div className="mb-4 text-sm text-gray-600">
                <p>Your upload request will be reviewed by the administrator.</p>
                <p>You will be notified when it's approved or rejected.</p>
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowUploadForm(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
} 