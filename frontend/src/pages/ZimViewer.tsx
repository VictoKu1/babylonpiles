import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

interface ZimFileInfo {
  name: string
  size: string
  path: string
  last_modified: string
}

export function ZimViewer() {
  const { filePath } = useParams<{ filePath: string }>()
  const navigate = useNavigate()
  const [fileInfo, setFileInfo] = useState<ZimFileInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showWebViewer, setShowWebViewer] = useState(false)

  useEffect(() => {
    if (!filePath) {
      setError('No file path provided')
      setLoading(false)
      return
    }

    // Get file info
    const fetchFileInfo = async () => {
      try {
        const response = await fetch(`/api/v1/files/view/${encodeURIComponent(filePath)}`)
        
        if (response.ok) {
          const result = await response.json()
          setFileInfo(result.data)
        } else {
          setError('File not found')
        }
      } catch (err) {
        setError('Error loading file information')
      } finally {
        setLoading(false)
      }
    }

    fetchFileInfo()
  }, [filePath])

  const zimFileUrl = filePath ? `/api/v1/files/download?path=${encodeURIComponent(filePath)}` : ''

  const openWithKiwix = () => {
    // Open with local Kiwix-Serve instance
    const zimFileName = filePath ? filePath.split('/').pop() : ''
    if (zimFileName) {
      window.open(`http://localhost:8081/${encodeURIComponent(zimFileName)}`, '_blank')
    }
  }

  const openWithSystemDefault = () => {
    // Download and let the system handle it
    const downloadUrl = `/api/v1/files/download?path=${encodeURIComponent(filePath || '')}`
    window.open(downloadUrl, '_blank', 'noopener,noreferrer')
  }

  const openWebViewer = () => {
    setShowWebViewer(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading ZIM file information...</p>
        </div>
      </div>
    )
  }

  if (error || !fileInfo) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">Error Loading ZIM File</h2>
          <p className="text-gray-600 mb-4">{error || 'File not found'}</p>
          <button
            onClick={() => navigate('/browse')}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Back to File Browser
          </button>
        </div>
      </div>
    )
  }

  if (showWebViewer) {
    return (
      <div className="h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setShowWebViewer(false)}
              className="bg-gray-500 text-white px-3 py-1 rounded hover:bg-gray-600"
            >
              ← Back to Options
            </button>
            <div>
              <h1 className="text-lg font-semibold">{fileInfo.name}</h1>
              <p className="text-sm text-gray-600">
                {fileInfo.size} • Open a downloaded archive in your browser
              </p>
            </div>
          </div>
          <div className="flex space-x-2">
            <a
              href={zimFileUrl}
              download={fileInfo.name}
              className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
            >
              Download
            </a>
          </div>
        </div>

        <div className="max-w-2xl mx-auto p-8 space-y-4">
          <h2 className="text-xl font-semibold">Open a local archive with Kiwix JS</h2>
          <ol className="list-decimal pl-6 space-y-3">
            <li>Download the ZIM archive using the Download button above.</li>
            <li>Open Kiwix JS and use its file picker to select the downloaded archive.</li>
          </ol>
          <p className="text-sm text-gray-600">The browser viewer reads the local file you select. It does not receive your BabylonPiles session or a link to your private archive.</p>
          <a href="https://kiwix.github.io/kiwix-js-windows/" target="_blank" rel="noopener noreferrer" className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Open Kiwix JS</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full p-8">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">📚</div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">ZIM File Viewer</h1>
          <p className="text-gray-600">Choose how to open your ZIM file</p>
        </div>

        {/* File Info */}
        <div className="bg-gray-50 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">File Information</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">Name:</span>
              <p className="text-gray-900">{fileInfo.name}</p>
            </div>
            <div>
              <span className="font-medium text-gray-700">Size:</span>
              <p className="text-gray-900">{fileInfo.size}</p>
            </div>
            <div>
              <span className="font-medium text-gray-700">Type:</span>
              <p className="text-gray-900">ZIM Archive (Offline Knowledge Base)</p>
            </div>
            <div>
              <span className="font-medium text-gray-700">Last Modified:</span>
              <p className="text-gray-900">{new Date(fileInfo.last_modified).toLocaleDateString()}</p>
            </div>
          </div>
        </div>

        {/* Opening Options */}
        <div className="space-y-4 mb-8">
          <h2 className="text-lg font-semibold">Opening Options</h2>
          
          {/* Option 1: Kiwix Desktop App */}
          <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                                 <h3 className="font-semibold text-green-700">🚀 Fastest: Kiwix-Serve (Docker)</h3>
                 <p className="text-sm text-gray-600">Open an archive already published by the operator to Kiwix-Serve on this computer.</p>
              </div>
                               <button
                   onClick={openWithKiwix}
                   className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                 >
                   Open with Kiwix-Serve
                 </button>
            </div>
          </div>

          {/* Option 2: System Default */}
          <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-blue-700">💾 Download & Open</h3>
                <p className="text-sm text-gray-600">Download the file and open with your system's default ZIM handler</p>
              </div>
              <button
                onClick={openWithSystemDefault}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Download & Open
              </button>
            </div>
          </div>

          {/* Option 3: Web Viewer */}
          <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-orange-700">🌐 Browser Viewer</h3>
                <p className="text-sm text-gray-600">Download the archive, then select it in Kiwix JS.</p>
              </div>
              <button
                onClick={openWebViewer}
                className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
              >
                Open in Browser
              </button>
            </div>
          </div>
        </div>

        {/* Additional Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <h3 className="font-semibold text-blue-800 mb-2">💡 Tips for Better Performance</h3>
                     <ul className="text-sm text-blue-700 space-y-1">
             <li>• Kiwix-Serve runs locally in Docker for fast access</li>
             <li>• Large ZIM files work perfectly with Kiwix-Serve</li>
             <li>• Kiwix-Serve is available on the server computer by default</li>
           </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <button
            onClick={() => navigate('/browse')}
            className="bg-gray-500 text-white px-6 py-2 rounded hover:bg-gray-600"
          >
            Back to File Browser
          </button>
          <a
            href={zimFileUrl}
            download={fileInfo.name}
            className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700"
          >
            Download ZIM File
          </a>
        </div>
      </div>
    </div>
  )
}
