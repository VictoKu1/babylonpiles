import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface FileItem {
  name: string;
  is_dir: boolean;
  size?: number;
  path: string;
  is_public?: boolean;
  metadata?: {
    creator: string;
    created_at: string;
    modified_at: string;
    size: number;
    is_dir: boolean;
  };
}

interface DownloadStatus {
  pile_id: number;
  pile_name: string;
  progress: number;
  is_downloading: boolean;
  file_path: string;
}

export default function Browse() {
  const [path, setPath] = useState<string>('');
  const [items, setItems] = useState<FileItem[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState<boolean>(false);
  const [folderName, setFolderName] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showViewer, setShowViewer] = useState(false)
  const [viewingFile, setViewingFile] = useState<FileItem | null>(null)
  const [fileViewInfo, setFileViewInfo] = useState<any>(null)
  const navigate = useNavigate()
  // Drag-and-drop state
  const [draggedItem, setDraggedItem] = useState<FileItem | null>(null);
  const [dragOverPath, setDragOverPath] = useState<string | null>(null);
  // Download status state
  const [downloadStatus, setDownloadStatus] = useState<Record<string, DownloadStatus>>({});
  // Metadata modal state
  const [showMetadataModal, setShowMetadataModal] = useState<boolean>(false);
  const [metadataInfo, setMetadataInfo] = useState<any>(null);
  const [metadataLoading, setMetadataLoading] = useState<boolean>(false);
  // Desktop drag and drop state
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [dragUploading, setDragUploading] = useState<boolean>(false);

  const fetchFiles = async (newPath: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8080/api/v1/files?path=${encodeURIComponent(newPath)}`);
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setItems(data.items.map((item: any) => ({
        name: item.name,
        is_dir: item.is_dir,
        size: item.size,
        path: newPath ? `${newPath}/${item.name}` : item.name,
        is_public: item.is_public,
        metadata: item.metadata
      })));
      setPath(data.path);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDownloadStatus = async () => {
    try {
      const res = await fetch('http://localhost:8080/api/v1/files/download-status');
      if (res.ok) {
        const data = await res.json();
        setDownloadStatus(data.data || {});
      }
    } catch (e) {
      console.error('Error fetching download status:', e);
    }
  };

  useEffect(() => {
    fetchFiles('');
    setHistory(['']);
    fetchDownloadStatus();
  }, []);

  // Poll for download status updates every 2 seconds
  useEffect(() => {
    const interval = setInterval(fetchDownloadStatus, 2000);
    return () => clearInterval(interval);
  }, []);

  const goTo = (newPath: string) => {
    fetchFiles(newPath);
    setHistory((h) => [...h, newPath]);
  };

  const goUp = () => {
    if (path === '' || path === '/') return;
    const parts = path.split('/').filter(Boolean);
    parts.pop();
    const upPath = parts.join('/');
    fetchFiles(upPath);
    setHistory((h) => [...h, upPath]);
  };

  const handleDownload = (fileName: string) => {
    const filePath = path ? `${path}/${fileName}` : fileName;
    window.open(`http://localhost:8080/api/v1/files/download?path=${encodeURIComponent(filePath)}`, '_blank');
  };

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!fileInputRef.current?.files?.length) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', fileInputRef.current.files[0]);
    formData.append('path', path);

    try {
      const res = await fetch('http://localhost:8080/api/v1/files/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await res.json();
      alert(data.message);
      setShowUploadModal(false);
      fetchFiles(path); // Refresh the file list
    } catch (e: any) {
      alert(`Upload failed: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleCreateFolder = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!folderName.trim()) return;

    try {
      const formData = new FormData();
      formData.append('folder_name', folderName.trim());
      formData.append('path', path);

      const res = await fetch('http://localhost:8080/api/v1/files/mkdir', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to create folder');
      }

      const data = await res.json();
      alert(data.message);
      setShowCreateFolderModal(false);
      setFolderName('');
      fetchFiles(path); // Refresh the file list
    } catch (e: any) {
      alert(`Failed to create folder: ${e.message}`);
    }
  };

  const handleDelete = async (itemName: string) => {
    if (!confirm(`Are you sure you want to delete "${itemName}"?`)) return;

    const itemPath = path ? `${path}/${itemName}` : itemName;
    
    try {
      const res = await fetch(`http://localhost:8080/api/v1/files/delete?path=${encodeURIComponent(itemPath)}`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Delete failed');
      }

      const data = await res.json();
      alert(data.message);
      fetchFiles(path); // Refresh the file list
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '-';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const getDownloadStatus = (fileName: string): DownloadStatus | null => {
    return downloadStatus[fileName] || null;
  };

  const renderDownloadProgress = (fileName: string) => {
    const status = getDownloadStatus(fileName);
    if (!status || !status.is_downloading) return null;

    return (
      <div className="flex items-center space-x-2 mt-1">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-blue-600 rounded-full animate-pulse"></div>
          <span className="text-xs text-blue-600">Downloading...</span>
        </div>
        <div className="w-16 bg-gray-200 rounded-full h-1">
          <div
            className="bg-blue-600 h-1 rounded-full transition-all duration-300"
            style={{ width: `${status.progress * 100}%` }}
          ></div>
        </div>
        <span className="text-xs text-gray-600">
          {Math.round(status.progress * 100)}%
        </span>
      </div>
    );
  };

  const handleViewFile = async (file: FileItem) => {
    const extension = file.name.split('.').pop()?.toLowerCase()
    
    // For ZIM files, navigate to the ZIM viewer page
    if (extension === 'zim') {
      navigate(`/zim-viewer/${encodeURIComponent(file.path)}`)
      return
    }
    
    // For other files, use the existing modal viewer
    try {
      const response = await fetch(`http://localhost:8080/api/v1/files/view/${encodeURIComponent(file.path)}`)
      
      if (response.ok) {
        const result = await response.json()
        setFileViewInfo(result.data)
        setViewingFile(file)
        setShowViewer(true)
      } else {
        alert('Error getting file information')
      }
    } catch (error) {
      console.error('Error viewing file:', error)
      alert('Error viewing file')
    }
  }

  const getViewButton = (file: FileItem) => {
    const extension = file.name.split('.').pop()?.toLowerCase()
    
    if (!extension) return null
    
    const viewableTypes = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'html', 'htm', 'txt', 'md', 'json', 'xml', 'csv', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'zim']
    
    if (viewableTypes.includes(extension)) {
      return (
        <button
          onClick={() => handleViewFile(file)}
          className="bg-blue-600 text-white px-2 py-1 rounded text-xs hover:bg-blue-700 mr-2"
        >
          {extension === 'zim' ? 'Open ZIM' : 'View'}
        </button>
      )
    }
    
    return null
  }

  // Move file/folder API
  const moveItem = async (src: string, dest: string) => {
    if (src === dest) return;
    const formData = new FormData();
    formData.append('src_path', src);
    formData.append('dest_path', dest);
    try {
      const res = await fetch('http://localhost:8080/api/v1/files/move', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Move failed');
      }
      fetchFiles(path);
    } catch (e: any) {
      alert(`Move failed: ${e.message}`);
    }
  };

  // Render '..' parent folder entry
  const parentEntry = path && path !== '' && path !== '/' ? (
    <tr
      key=".."
      // NOT draggable
      onDragOver={e => { e.preventDefault(); setDragOverPath('..'); }}
      onDragLeave={() => setDragOverPath(null)}
      onDrop={e => {
        e.preventDefault();
        setDragOverPath(null);
        if (draggedItem) {
          // Move to parent folder
          const parts = path.split('/').filter(Boolean);
          parts.pop();
          const parentPath = parts.join('/');
          const dest = parentPath ? `${parentPath}/${draggedItem.name}` : draggedItem.name;
          moveItem(draggedItem.path, dest);
        }
      }}
      style={{ background: dragOverPath === '..' ? '#ffe082' : undefined, border: dragOverPath === '..' ? '2px dashed #ffb300' : undefined }}
    >
      <td colSpan={5} style={{ fontWeight: 'bold', cursor: 'pointer' }} onClick={goUp}>
        .. (parent folder)
      </td>
    </tr>
  ) : null;

  // Add debug output for drag-and-drop
  useEffect(() => {
    if (draggedItem) {
      console.log('Dragging:', draggedItem.name, 'from', draggedItem.path);
    }
    if (dragOverPath) {
      console.log('Drag over:', dragOverPath);
    }
  }, [draggedItem, dragOverPath]);

  const handleTogglePermission = async (item: FileItem) => {
    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/files/permission/${encodeURIComponent(item.path)}/toggle`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        const result = await response.json();
        console.log("Permission toggled:", result);
        
        // Show success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300';
        notification.textContent = result.message || 'Permission updated successfully';
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
          notification.style.transform = 'translateX(100%)';
          setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
        
        // Refresh the file list to get updated permissions
        fetchFiles(path);
      } else {
        let errorMessage = 'Failed to toggle permission';
        
        try {
          const errorData = await response.json();
          console.error("Permission toggle failed:", errorData);
          
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.message) {
            errorMessage = errorData.message;
          } else if (typeof errorData === 'string') {
            errorMessage = errorData;
          } else {
            errorMessage = `Server error: ${response.status}`;
          }
        } catch (parseError) {
          console.error("Failed to parse error response:", parseError);
          errorMessage = `Server error: ${response.status}`;
        }
        
        // Show error notification
        const errorNotification = document.createElement('div');
        errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300';
        errorNotification.textContent = errorMessage;
        document.body.appendChild(errorNotification);
        
        // Remove error notification after 5 seconds
        setTimeout(() => {
          errorNotification.style.transform = 'translateX(100%)';
          setTimeout(() => document.body.removeChild(errorNotification), 300);
        }, 5000);
      }
    } catch (error) {
      console.error("Error toggling permission:", error);
      
      // Show error notification
      const errorNotification = document.createElement('div');
      errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300';
      errorNotification.textContent = 'Network error: Unable to toggle permission';
      document.body.appendChild(errorNotification);
      
      // Remove error notification after 5 seconds
      setTimeout(() => {
        errorNotification.style.transform = 'translateX(100%)';
        setTimeout(() => document.body.removeChild(errorNotification), 300);
      }, 5000);
    }
  };

  const getPermissionIcon = (isPublic: boolean) => {
    return isPublic ? "🌐" : "🔒";
  };

  const getPermissionTooltip = (isPublic: boolean) => {
    return isPublic ? "Public - Click to make private" : "Private - Click to make public";
  };

  const handleShowMetadata = async (item: FileItem) => {
    setMetadataLoading(true);
    setShowMetadataModal(true);
    
    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/files/metadata/${encodeURIComponent(item.path)}`
      );
      
      if (response.ok) {
        const result = await response.json();
        setMetadataInfo(result.data);
      } else {
        const errorData = await response.json();
        console.error("Failed to get metadata:", errorData);
        alert(`Failed to get metadata: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error getting metadata:", error);
      alert("Error getting metadata");
    } finally {
      setMetadataLoading(false);
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

  // Desktop drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    setDragUploading(true);
    
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file as File);
        formData.append('path', path);

        const res = await fetch('http://localhost:8080/api/v1/files/upload', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || `Upload failed for ${(file as File).name}`);
        }
      }

      // Show a more user-friendly success message
      const message = files.length === 1 
        ? `File "${(files[0] as File).name}" added to drive successfully!`
        : `${files.length} files added to drive successfully!`;
      
      // Use a custom notification instead of alert
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300';
      notification.textContent = message;
      document.body.appendChild(notification);
      
      // Remove notification after 3 seconds
      setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => document.body.removeChild(notification), 300);
      }, 3000);
      
      fetchFiles(path); // Refresh the file list
    } catch (e: any) {
      // Show a user-friendly error notification
      const errorNotification = document.createElement('div');
      errorNotification.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-all duration-300';
      errorNotification.textContent = `Failed to add files: ${e.message}`;
      document.body.appendChild(errorNotification);
      
      // Remove error notification after 5 seconds
      setTimeout(() => {
        errorNotification.style.transform = 'translateX(100%)';
        setTimeout(() => document.body.removeChild(errorNotification), 300);
      }, 5000);
    } finally {
      setDragUploading(false);
    }
  };

  return (
    <div 
      className={`p-6 min-h-screen ${isDragOver ? 'bg-blue-50 border-2 border-dashed border-blue-400' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <h1 className="text-2xl font-bold mb-4">File Browser</h1>
      
      {/* Drag and drop upload indicator */}
      {isDragOver && (
        <div className="fixed inset-0 bg-blue-500 bg-opacity-30 flex items-center justify-center z-50 pointer-events-none">
          <div className="bg-white p-6 rounded-xl shadow-2xl border-2 border-dashed border-blue-500 transform scale-105 transition-all duration-200">
            <div className="text-center">
              <div className="text-5xl mb-3">📁</div>
              <div className="text-lg font-bold text-blue-600 mb-1">Drop to Add Files</div>
              <div className="text-sm text-gray-500">Files will be added to: <span className="font-mono text-blue-600">{path || 'root'}</span></div>
            </div>
          </div>
        </div>
      )}
      
      {/* Upload progress indicator */}
      {dragUploading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-2xl">
            <div className="text-center">
              <div className="text-3xl mb-3">📤</div>
              <div className="text-lg font-bold mb-2 text-blue-600">Adding Files to Drive</div>
              <div className="text-sm text-gray-600 mb-3">Please wait while files are being uploaded</div>
              <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
            </div>
          </div>
        </div>
      )}
      {/* Drag-and-drop debug info */}
      {draggedItem && (
        <div className="mb-2 p-2 bg-yellow-100 border border-yellow-400 rounded text-yellow-800">
          Dragging: <b>{draggedItem.name}</b> from <span className="font-mono">{draggedItem.path}</span>
          {dragOverPath && (
            <span> &rarr; <b>{dragOverPath === '..' ? '.. (parent folder)' : dragOverPath}</b></span>
          )}
        </div>
      )}
      
      {/* Navigation and Actions */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button onClick={goUp} className="bg-gray-200 px-3 py-1 rounded text-sm hover:bg-gray-300">
            ↑ Up
          </button>
          <span className="text-gray-600 font-mono">{path || '/'}</span>
        </div>
        
        <div className="flex space-x-2">
          <button 
            onClick={() => setShowUploadModal(true)}
            className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
          >
            Upload File
          </button>
          <button 
            onClick={() => setShowCreateFolderModal(true)}
            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
          >
            New Folder
          </button>
        </div>
      </div>



      {/* Error and Loading */}
      {loading && <div className="text-blue-600 mb-2">Loading...</div>}
      {error && <div className="text-red-600 mb-2">{error}</div>}

      {/* File List */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Name</th>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Type</th>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Size</th>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Access</th>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Info</th>
              <th className="text-left px-4 py-2 font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {parentEntry}
            {items.map((item) => (
              <tr
                key={item.name}
                draggable
                onDragStart={() => setDraggedItem(item)}
                onDragEnd={() => setDraggedItem(null)}
                onDragOver={e => { e.preventDefault(); setDragOverPath(item.path); }}
                onDragLeave={() => setDragOverPath(null)}
                onDrop={e => {
                  e.preventDefault();
                  setDragOverPath(null);
                  if (draggedItem && item.is_dir && draggedItem.path !== item.path) {
                    // Move into this folder
                    const dest = `${item.path}/${draggedItem.name}`;
                    moveItem(draggedItem.path, dest);
                  }
                }}
                style={{ background: dragOverPath === item.path ? '#ffe082' : undefined, border: dragOverPath === item.path ? '2px dashed #ffb300' : undefined }}
              >
                <td className="px-4 py-2">
                  <div>
                    {item.is_dir ? (
                      <button 
                        className="text-blue-600 hover:underline flex items-center"
                        onClick={() => goTo(path ? `${path}/${item.name}` : item.name)}
                      >
                        📁 {item.name}
                      </button>
                    ) : (
                      <div>
                        <span className="flex items-center">📄 {item.name}</span>
                        {renderDownloadProgress(item.name)}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {item.is_dir ? 'Folder' : 'File'}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {formatFileSize(item.size)}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => handleTogglePermission(item)}
                    className="text-lg hover:scale-110 transition-transform"
                    title={getPermissionTooltip(item.is_public || false)}
                  >
                    {getPermissionIcon(item.is_public || false)}
                  </button>
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => handleShowMetadata(item)}
                    className="text-lg hover:scale-110 transition-transform text-blue-600"
                    title="View file information"
                  >
                    ℹ️
                  </button>
                </td>
                <td className="px-4 py-2">
                  <div className="flex space-x-2">
                    {!item.is_dir && (
                      <button 
                        className="bg-green-600 text-white px-2 py-1 rounded text-xs hover:bg-green-700"
                        onClick={() => handleDownload(item.name)}
                      >
                        Download
                      </button>
                    )}
                    <button 
                      className="bg-red-600 text-white px-2 py-1 rounded text-xs hover:bg-red-700"
                      onClick={() => handleDelete(item.name)}
                    >
                      Delete
                    </button>
                    {getViewButton(item)}
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No files or folders found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h2 className="text-lg font-bold mb-4">Upload File</h2>
            <form onSubmit={handleUpload}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select File
                </label>
                <input
                  type="file"
                  ref={fileInputRef}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  required
                />
              </div>
              <div className="flex space-x-2">
                <button
                  type="submit"
                  disabled={uploading}
                  className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Folder Modal */}
      {showCreateFolderModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full mx-4">
            <h2 className="text-lg font-bold mb-4">Create New Folder</h2>
            <form onSubmit={handleCreateFolder}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Folder Name
                </label>
                <input
                  type="text"
                  value={folderName}
                  onChange={(e) => setFolderName(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                  placeholder="Enter folder name"
                  required
                />
              </div>
              <div className="flex space-x-2">
                <button
                  type="submit"
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateFolderModal(false);
                    setFolderName('');
                  }}
                  className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* File Viewer Modal */}
      {showViewer && viewingFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">View File: {viewingFile.name}</h2>
              <button
                onClick={() => setShowViewer(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>
            
            {fileViewInfo && (
              <div>
                <div className="mb-4 p-3 bg-gray-50 rounded">
                  <p><strong>File:</strong> {fileViewInfo.name}</p>
                  <p><strong>Size:</strong> {fileViewInfo.size_formatted}</p>
                  <p><strong>Type:</strong> {fileViewInfo.view_type.toUpperCase()}</p>
                  <p><strong>Last Modified:</strong> {new Date(fileViewInfo.last_modified).toLocaleString()}</p>
                </div>
                
                {viewingFile.is_dir ? (
                  <p>This is a directory. No content to display.</p>
                ) : (
                  <div className="border rounded p-4">
                    {fileViewInfo.view_type === 'pdf' ? (
                      <iframe
                        src={`http://localhost:8080/api/v1/files/preview/${encodeURIComponent(viewingFile.path)}`}
                        width="100%"
                        height="600px"
                        title="PDF Viewer"
                        className="border"
                      />
                    ) : fileViewInfo.view_type === 'image' ? (
                      <div className="text-center">
                        <img
                          src={`http://localhost:8080/api/v1/files/preview/${encodeURIComponent(viewingFile.path)}`}
                          alt={viewingFile.name}
                          className="max-w-full max-h-96 mx-auto"
                          style={{ objectFit: 'contain' }}
                        />
                      </div>
                    ) : fileViewInfo.view_type === 'video' ? (
                      <video
                        src={`http://localhost:8080/api/v1/files/preview/${encodeURIComponent(viewingFile.path)}`}
                        width="100%"
                        height="400px"
                        controls
                        className="mx-auto"
                      />
                    ) : fileViewInfo.view_type === 'audio' ? (
                      <div className="text-center">
                        <audio
                          src={`http://localhost:8080/api/v1/files/preview/${encodeURIComponent(viewingFile.path)}`}
                          controls
                          className="mx-auto"
                        />
                      </div>
                    ) : fileViewInfo.view_type === 'text' ? (
                      <iframe
                        src={`http://localhost:8080/api/v1/files/preview/${encodeURIComponent(viewingFile.path)}`}
                        width="100%"
                        height="500px"
                        title="Text Viewer"
                        className="border"
                      />
                    ) : fileViewInfo.view_type === 'zim' ? (
                      <div className="text-center p-8">
                        <h3 className="text-lg font-semibold mb-4">ZIM File Viewer</h3>
                        <p className="mb-4">This is a ZIM file containing offline content.</p>
                        <div className="space-y-2">
                          <a
                            href={`http://localhost:8080/api/v1/files/zim-viewer/${encodeURIComponent(viewingFile.path)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 inline-block"
                          >
                            Open ZIM Viewer
                          </a>
                          <br />
                          <a
                            href={`http://localhost:8080/api/v1/files/download/${encodeURIComponent(viewingFile.path)}`}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 inline-block"
                          >
                            Download ZIM File
                          </a>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center p-8">
                        <p className="mb-4">This file type cannot be previewed in the browser.</p>
                        <a
                          href={`http://localhost:8080/api/v1/files/download/${encodeURIComponent(viewingFile.path)}`}
                          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                        >
                          Download File
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            <div className="mt-4 flex justify-end space-x-2">
              <a
                href={`http://localhost:8080/api/v1/files/download/${encodeURIComponent(viewingFile.path)}`}
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Download
              </a>
              <button
                onClick={() => setShowViewer(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Metadata Modal */}
      {showMetadataModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold">
                {metadataLoading ? "Loading..." : metadataInfo?.name || "File Information"}
              </h2>
              <button
                onClick={() => setShowMetadataModal(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>
            
            {metadataLoading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-600">Loading file information...</p>
              </div>
            ) : metadataInfo ? (
              <div className="space-y-4">
                {/* Basic Information */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">Basic Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-600">Name:</span>
                      <p className="text-gray-900">{metadataInfo.name}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600">Type:</span>
                      <p className="text-gray-900">{metadataInfo.is_dir ? "Folder" : "File"}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600">Size:</span>
                      <p className="text-gray-900">{metadataInfo.size_formatted}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600">Access:</span>
                      <p className="text-gray-900">
                        {metadataInfo.is_public ? "🌐 Public" : "🔒 Private"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Creator Information */}
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">Creator Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-blue-700">Created by:</span>
                      <p className="text-blue-900">{metadataInfo.creator}</p>
                    </div>
                    <div>
                      <span className="font-medium text-blue-700">Created:</span>
                      <p className="text-blue-900">{formatDate(metadataInfo.created_at)}</p>
                    </div>
                    <div>
                      <span className="font-medium text-blue-700">Created ago:</span>
                      <p className="text-blue-900">{metadataInfo.created_ago}</p>
                    </div>
                    <div>
                      <span className="font-medium text-blue-700">Modified:</span>
                      <p className="text-blue-900">{formatDate(metadataInfo.modified_at)}</p>
                    </div>
                    <div>
                      <span className="font-medium text-blue-700">Modified ago:</span>
                      <p className="text-blue-900">{metadataInfo.modified_ago}</p>
                    </div>
                  </div>
                </div>

                {/* File Details */}
                {!metadataInfo.is_dir && (
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-green-900 mb-2">File Details</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-green-700">Extension:</span>
                        <p className="text-green-900">{metadataInfo.file_info.extension || "None"}</p>
                      </div>
                      <div>
                        <span className="font-medium text-green-700">MIME Type:</span>
                        <p className="text-green-900">{metadataInfo.file_info.mime_type}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Permissions */}
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-yellow-900 mb-2">Permissions</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-yellow-700">Owner Read:</span>
                      <p className="text-yellow-900">{metadataInfo.permissions.owner_read ? "✅ Yes" : "❌ No"}</p>
                    </div>
                    <div>
                      <span className="font-medium text-yellow-700">Owner Write:</span>
                      <p className="text-yellow-900">{metadataInfo.permissions.owner_write ? "✅ Yes" : "❌ No"}</p>
                    </div>
                    <div>
                      <span className="font-medium text-yellow-700">Public Read:</span>
                      <p className="text-yellow-900">{metadataInfo.permissions.public_read ? "✅ Yes" : "❌ No"}</p>
                    </div>
                    <div>
                      <span className="font-medium text-yellow-700">Public Write:</span>
                      <p className="text-yellow-900">{metadataInfo.permissions.public_write ? "✅ Yes" : "❌ No"}</p>
                    </div>
                  </div>
                </div>

                {/* System Information */}
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-2">System Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium text-gray-600">Inode:</span>
                      <p className="text-gray-900">{metadataInfo.file_info.inode}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-600">Device:</span>
                      <p className="text-gray-900">{metadataInfo.file_info.device}</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                Failed to load file information
              </div>
            )}
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowMetadataModal(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 