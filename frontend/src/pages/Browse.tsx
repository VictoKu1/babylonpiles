import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

interface FileItem {
  name: string;
  is_dir: boolean;
  size?: number;
  path: string;
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
        path: newPath ? `${newPath}/${item.name}` : item.name
      })));
      setPath(data.path);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles('');
    setHistory(['']);
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

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">File Browser</h1>
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
                  {item.is_dir ? (
                    <button 
                      className="text-blue-600 hover:underline flex items-center"
                      onClick={() => goTo(path ? `${path}/${item.name}` : item.name)}
                    >
                      📁 {item.name}
                    </button>
                  ) : (
                    <span className="flex items-center">📄 {item.name}</span>
                  )}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {item.is_dir ? 'Folder' : 'File'}
                </td>
                <td className="px-4 py-2 text-gray-600">
                  {formatFileSize(item.size)}
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
                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
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
    </div>
  );
} 