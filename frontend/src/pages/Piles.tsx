import React, { useState, useEffect } from "react";

interface Pile {
  id?: number;
  name: string;
  display_name: string;
  description: string;
  category: string;
  source_type: "kiwix" | "http" | "torrent";
  source_url: string;
  tags?: string[];
  file_path?: string;
  file_size?: number;
  is_downloading?: boolean;
  download_progress?: number;
}

interface QuickAddSource {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  source_type: "kiwix" | "http" | "torrent";
  source_url: string;
  tags: string[];
  size?: string;
  difficulty: "easy" | "moderate" | "advanced";
}

interface GutenbergBook {
  id: number;
  title: string;
  authors: { name: string }[];
  subjects: string[];
  formats: Record<string, string>;
  download_count: number;
}

const QUICK_ADD_SOURCES: QuickAddSource[] = [
  // Lightweight/Moderate-Size Sources
  {
    id: "wikipedia_en_all",
    name: "wikipedia_en_all",
    display_name: "Wikipedia English (Complete)",
    description:
      "Complete English Wikipedia with all articles and images. Essential offline knowledge base.",
    category: "education",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/wikipedia_en_all.zim",
    tags: ["wikipedia", "education", "knowledge", "offline"],
    size: "~80 GB",
    difficulty: "moderate",
  },
  {
    id: "wikipedia_en_medical",
    name: "wikipedia_en_medical",
    display_name: "WikiMed (Medical Wikipedia)",
    description:
      "Medical articles subset of Wikipedia. Ideal for health and emergency medicine.",
    category: "medical",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/wikipedia_en_medicine.zim",
    tags: ["medical", "health", "emergency", "wikipedia"],
    size: "~75k pages",
    difficulty: "easy",
  },
  {
    id: "gutenberg_en_all",
    name: "gutenberg_en_all",
    display_name: "Project Gutenberg Books",
    description:
      "~60k public-domain eBooks including literature, science, and history classics.",
    category: "books",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/gutenberg_en_all.zim",
    tags: ["books", "literature", "classics", "public-domain"],
    size: "~30-40 GB",
    difficulty: "moderate",
  },
  {
    id: "wikipedia_en_simple",
    name: "wikipedia_en_simple",
    display_name: "Wikipedia Simple English",
    description:
      "Simplified English Wikipedia with easier language for learning and basic reference.",
    category: "education",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/wikipedia_en_simple_all.zim",
    tags: ["wikipedia", "simple", "learning", "basic"],
    size: "~1 GB",
    difficulty: "easy",
  },
  {
    id: "wiktionary_en_all",
    name: "wiktionary_en_all",
    display_name: "Wiktionary English Dictionary",
    description:
      "Complete English dictionary and thesaurus with definitions, pronunciations, and etymology.",
    category: "education",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/wiktionary_en_all.zim",
    tags: ["dictionary", "language", "reference", "definitions"],
    size: "~2 GB",
    difficulty: "easy",
  },
  {
    id: "wikivoyage_en_all",
    name: "wikivoyage_en_all",
    display_name: "Wikivoyage Travel Guide",
    description:
      "Comprehensive travel guides for destinations worldwide with maps and practical information.",
    category: "travel",
    source_type: "kiwix",
    source_url: "https://download.kiwix.org/zim/wikivoyage_en_all.zim",
    tags: ["travel", "guides", "maps", "destinations"],
    size: "~1 GB",
    difficulty: "easy",
  },
  // Test with a smaller, reliable file
  {
    id: "test_small_file",
    name: "test_small_file",
    display_name: "Test Small File",
    description:
      "A small test file to verify download functionality works correctly.",
    category: "general",
    source_type: "http",
    source_url: "https://httpbin.org/bytes/1024",
    tags: ["test", "small", "verification"],
    size: "~1 KB",
    difficulty: "easy",
  },
];

// --- KiwixTreeBrowser Component ---
interface KiwixNode {
  name: string;
  url: string;
  is_dir: boolean;
  size: number | null;
  children?: KiwixNode[];
  loaded?: boolean;
  last_modified?: string;
  loading?: boolean; // Added loading state
}

function formatFileSize(bytes: number | null | undefined) {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function flattenSelected(node: KiwixNode, selected: Record<string, boolean>): KiwixNode[] {
  if (!node.is_dir && selected[node.url]) return [node];
  if (node.is_dir && selected[node.url]) {
    // If folder is selected, all children are implicitly selected
    return node.children?.flatMap(child => flattenSelected(child, selected)) || [];
  }
  if (node.is_dir) {
    return node.children?.flatMap(child => flattenSelected(child, selected)) || [];
  }
  return [];
}

// Helper to sum sizes recursively
function getFolderSize(node: KiwixNode): number | null {
  if (!node.is_dir) return node.size || 0;
  if (!node.children) return null;
  let total = 0;
  let hasFile = false;
  for (const child of node.children) {
    const childSize = getFolderSize(child);
    if (childSize !== null) {
      total += childSize;
      hasFile = true;
    }
  }
  return hasFile ? total : null;
}

// Helper to get indeterminate state
function isIndeterminate(node: KiwixNode, selected: Record<string, boolean>): boolean {
  if (!node.is_dir || !node.children) return false;
  let checked = 0, unchecked = 0;
  for (const child of node.children) {
    if (child.is_dir && child.children) {
      if (isIndeterminate(child, selected)) return true;
    }
    if (selected[child.url]) checked++;
    else unchecked++;
  }
  return checked > 0 && unchecked > 0;
}

function TreeCheckbox({
  checked,
  indeterminate,
  onChange,
}: {
  checked: boolean;
  indeterminate: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  const ref = React.useRef<HTMLInputElement>(null);
  React.useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      type="checkbox"
      ref={ref}
      checked={checked}
      onChange={onChange}
      style={{ marginRight: 4 }}
    />
  );
}

const KiwixTreeBrowser: React.FC<{
  onDownload: (files: KiwixNode[]) => void;
}> = ({ onDownload }) => {
  const [sources, setSources] = useState<{ [name: string]: [string, string] }>({});
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [selectedRepoUrl, setSelectedRepoUrl] = useState<string | null>(null);
  const [selectedDescUrl, setSelectedDescUrl] = useState<string | null>(null);
  const [root, setRoot] = useState<KiwixNode[]>([]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [loadingFolders, setLoadingFolders] = useState<Record<string, boolean>>({});
  const [showModal, setShowModal] = useState(false);
  const [modalFiles, setModalFiles] = useState<KiwixNode[]>([]);
  const [searchText, setSearchText] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [infoModalHtml, setInfoModalHtml] = useState<string | null>(null);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [infoModalTitle, setInfoModalTitle] = useState('');
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [manualName, setManualName] = useState('');
  const [manualRepoUrl, setManualRepoUrl] = useState('');
  const [manualInfoUrl, setManualInfoUrl] = useState('');
  const [manualNoInfo, setManualNoInfo] = useState(false);
  const [manualError, setManualError] = useState('');

  useEffect(() => {
    fetch("http://localhost:8080/api/v1/piles/sources-list")
      .then(res => res.json())
      .then(data => setSources(data));
  }, []);

  useEffect(() => {
    if (!selectedSource || !sources[selectedSource]) return;
    setSelectedRepoUrl(sources[selectedSource][0]);
    setSelectedDescUrl(sources[selectedSource][1]);
  }, [selectedSource, sources]);

  useEffect(() => {
    if (!selectedRepoUrl) return;
    setLoading(true);
    fetch(`http://localhost:8080/api/v1/piles/browse-source?url=${encodeURIComponent(selectedRepoUrl)}&description_url=${encodeURIComponent(selectedDescUrl || '')}`)
      .then(res => res.json())
      .then(data => setRoot(data.items))
      .finally(() => setLoading(false));
  }, [selectedRepoUrl, selectedDescUrl]);

  // Prefetch children recursively in the background
  async function prefetchChildren(node: KiwixNode, updateNode: (n: KiwixNode) => void) {
    if (!node.is_dir || node.loaded) return;
    // Mark as loading
    updateNode({ ...node, loading: true });
    const res = await fetch(`http://localhost:8080/api/v1/piles/browse-source?url=${encodeURIComponent(node.url)}`);
    const data = await res.json();
    node.children = data.items;
    node.loaded = true;
    updateNode({ ...node, children: node.children, loaded: true, loading: false });
    // Recursively prefetch children
    for (const child of node.children) {
      prefetchChildren(child, updateNode);
    }
  }

  useEffect(() => {
    if (!root.length) return;
    // Helper to update a node in the root tree by reference
    const updateNode = (updated: KiwixNode) => {
      setRoot(r => [...r]);
    };
    for (const node of root) {
      prefetchChildren(node, updateNode);
    }
    // eslint-disable-next-line
  }, [root.length]);

  const loadChildren = async (node: KiwixNode) => {
    setLoadingFolders(prev => ({ ...prev, [node.url]: true }));
    const res = await fetch(`http://localhost:8080/api/v1/piles/browse-source?url=${encodeURIComponent(node.url)}`);
    const data = await res.json();
    node.children = data.items;
    node.loaded = true;
    setLoadingFolders(prev => ({ ...prev, [node.url]: false }));
    setRoot(r => [...r]);
  };

  const toggleExpand = async (node: KiwixNode) => {
    setExpanded(prev => ({ ...prev, [node.url]: !prev[node.url] }));
    if (node.is_dir && !node.loaded && !loadingFolders[node.url]) {
      await loadChildren(node);
    }
  };

  const toggleSelect = (node: KiwixNode, checked: boolean) => {
    const update = (n: KiwixNode, value: boolean): Record<string, boolean> => {
      let updates: Record<string, boolean> = { [n.url]: value };
      if (n.is_dir && n.children) {
        n.children.forEach(child => {
          updates = { ...updates, ...update(child, value) };
        });
      }
      return updates;
    };
    setSelected(prev => ({ ...prev, ...update(node, checked) }));
  };

  function flattenSelected(node: KiwixNode, selected: Record<string, boolean>): KiwixNode[] {
    if (!node.is_dir && selected[node.url]) return [node];
    if (node.is_dir && selected[node.url] && node.children) {
      return node.children.flatMap(child => flattenSelected(child, selected));
    }
    if (node.is_dir && node.children) {
      return node.children.flatMap(child => flattenSelected(child, selected));
    }
    return [];
  }

  // Helper to extract field values from file names
  function extractFieldValues(nodes: KiwixNode[], maxFields = 5): Record<string, Set<string>> {
    const fieldValues: Record<string, Set<string>> = {};
    function visit(node: KiwixNode) {
      if (!node.is_dir && node.name.endsWith('.zim')) {
        const parts = node.name.replace('.zim', '').split('_');
        for (let i = 0; i < Math.min(parts.length, maxFields); i++) {
          const key = `field${i+1}`;
          if (!fieldValues[key]) fieldValues[key] = new Set();
          fieldValues[key].add(parts[i]);
        }
      }
      if (node.is_dir && node.children) {
        node.children.forEach(visit);
      }
    }
    nodes.forEach(visit);
    return fieldValues;
  }

  // Helper to filter files by selected field values
  function fileMatchesFilters(node: KiwixNode, filters: Record<string, string | null>, maxFields = 5, searchText = ''): boolean {
    if (searchText && !node.name.toLowerCase().includes(searchText.toLowerCase())) return false;
    if (node.is_dir) return true;
    if (!node.name.endsWith('.zim')) return true;
    const parts = node.name.replace('.zim', '').split('_');
    for (let i = 0; i < maxFields; i++) {
      const key = `field${i+1}`;
      if (filters[key] && parts[i] !== filters[key]) return false;
    }
    return true;
  }

  const [filters, setFilters] = useState<Record<string, string | null>>({});
  const maxFields = 5;
  const fieldValues = React.useMemo(() => extractFieldValues(root, maxFields), [root]);

  const renderNode = (node: KiwixNode, depth = 0): JSX.Element | null => {
    // If this is a folder, check if any children match the filters/search
    let visibleChildren: KiwixNode[] = [];
    if (node.is_dir && node.children) {
      visibleChildren = node.children.filter(child => fileMatchesFilters(child, filters, maxFields, searchText));
      // If folder doesn't match search/filter and has no visible children, don't render it
      if (!fileMatchesFilters(node, filters, maxFields, searchText) && visibleChildren.length === 0) {
        return null;
      }
    } else if (!fileMatchesFilters(node, filters, maxFields, searchText)) {
      // If file doesn't match, don't render it
      return null;
    }
    const indeterminate = isIndeterminate(node, selected);
    const size = node.is_dir ? getFolderSize(node) : node.size;
    return (
      <div key={node.url} style={{ marginLeft: depth * 16 }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {node.is_dir ? (
            <span
              style={{ cursor: "pointer", marginRight: 4, userSelect: 'none' }}
              onClick={() => toggleExpand(node)}
            >
              {expanded[node.url] ? '▼' : '▶'}
            </span>
          ) : (
            <span style={{ width: 16, display: 'inline-block' }}></span>
          )}
          <TreeCheckbox
            checked={!!selected[node.url]}
            indeterminate={indeterminate}
            onChange={e => toggleSelect(node, e.target.checked)}
          />
          <span style={{ fontWeight: node.is_dir ? 600 : undefined }}>
            {node.is_dir ? '📁' : ''} {node.name}
          </span>
          {node.last_modified && (
            <span style={{ marginLeft: 8, color: "#888", fontSize: 12 }}>
              {node.last_modified}
            </span>
          )}
          {size !== null && (
            <span style={{ marginLeft: 8, color: "#888", fontSize: 12 }}>
              {formatFileSize(size)}
            </span>
          )}
          {/* Move the i button here, after name/date/size */}
          {!node.is_dir && selectedDescUrl && selectedDescUrl !== 'None' && (
            <button
              onClick={() => showFileInfo(node.name)}
              style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', fontSize: 16 }}
              title="Show file info"
            >
              ℹ️
            </button>
          )}
          {/* Filtering dropdowns for the currently expanded folder */}
          {node.is_dir && expanded[node.url] && node.children && (() => {
            const localFieldValues = extractFieldValues(node.children, maxFields);
            return Object.entries(localFieldValues).map(([key, values], idx) => (
              <select
                key={key}
                value={filters[key] || ''}
                onChange={e => setFilters(f => ({ ...f, [key]: e.target.value || null }))}
                style={{ marginLeft: 8, marginBottom: 0, width: 140, minWidth: 90, maxWidth: 180, textOverflow: 'ellipsis', whiteSpace: 'nowrap', overflow: 'hidden', display: 'inline-block' }}
              >
                <option value='' style={{ whiteSpace: 'normal' }}>{`--Filter ${idx + 1}--`}</option>
                {[...values].sort().map(v => (
                  <option key={v} value={v} style={{ whiteSpace: 'normal' }}>{v}</option>
                ))}
              </select>
            ));
          })()}
          {node.is_dir && node.loading && (
            <span style={{ marginLeft: 8, color: '#888', fontSize: 12 }}>(calculating...)</span>
          )}
        </div>
        {node.is_dir && expanded[node.url] && visibleChildren.length > 0 && (
          <div>
            {visibleChildren.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const handleDownloadClick = () => {
    const files = root.flatMap(node => flattenSelected(node, selected));
    setModalFiles(files);
    setShowModal(true);
  };

  const totalSize = modalFiles.reduce((sum, f) => sum + (f.size || 0), 0);

  // Helper to get all visible root node URLs
  function getAllRootUrls(nodes: KiwixNode[]): string[] {
    let urls: string[] = [];
    for (const node of nodes) {
      urls.push(node.url);
      if (node.is_dir && node.children) {
        urls = urls.concat(getAllRootUrls(node.children));
      }
    }
    return urls;
  }

  function getBaseFilename(filename: string): string {
    // Remove date and extension (e.g., africanstorybook.org_mul_all_2024-10.zim -> africanstorybook.org_mul_all_)
    return filename.replace(/_\d{4}-\d{2}\.zim$/, '_');
  }

  async function showFileInfo(filename: string) {
    if (!selectedDescUrl) return;
    const baseFilename = getBaseFilename(filename);
    setInfoModalTitle(filename);
    setInfoModalHtml('<div>Loading...</div>');
    setInfoModalOpen(true);
    const url = `http://localhost:8080/api/v1/piles/file-info?filename=${encodeURIComponent(baseFilename)}&description_url=${encodeURIComponent(selectedDescUrl)}`;
    try {
      const resp = await fetch(url);
      const html = await resp.text();
      let infoFields = null;
      try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const book = doc.querySelector('book');
        if (book) {
          infoFields = {
            title: book.getAttribute('title') || '',
            description: book.getAttribute('description') || '',
            language: book.getAttribute('language') || '',
            creator: book.getAttribute('creator') || '',
            publisher: book.getAttribute('publisher') || '',
          };
        }
      } catch (e) {
        // Parsing failed, infoFields remains null
      }
      // Only set the modal content after loading is done
      if (infoFields) {
        setInfoModalHtml(`
          <div style='line-height:1.7'>
            <div><b>Title:</b> ${infoFields.title}</div>
            <div><b>Description:</b> ${infoFields.description}</div>
            <div><b>Language:</b> ${infoFields.language}</div>
            <div><b>Creator:</b> ${infoFields.creator}</div>
            <div><b>Publisher:</b> ${infoFields.publisher}</div>
          </div>
        `);
      } else {
        setInfoModalHtml(`<div style='color:red'>No info found or failed to render info.</div>`);
      }
    } catch (e) {
      setInfoModalHtml(`<div style='color:red'>No info found or failed to render info.</div>`);
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-lg font-medium text-gray-900 mb-4">Browse Content Source</h2>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Select Source</label>
        <select
          value={selectedSource || ""}
          onChange={e => {
            if (e.target.value === '__manual__') {
              setManualModalOpen(true);
            } else {
              setSelectedSource(e.target.value || null);
            }
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Choose a source --</option>
          {Object.entries(sources).map(([name]) => (
            <option key={name} value={name}>{name}</option>
          ))}
          <option value="__manual__">Manual Entry...</option>
        </select>
      </div>
      {selectedSource && sources[selectedSource] && (
        <div style={{ margin: '4px 0 12px 0', color: '#555', fontSize: 13 }}>
          <span>Repository URL: </span>
          <span style={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>{sources[selectedSource][0]}</span>
        </div>
      )}
      {/* Select All Checkbox */}
      {root.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <TreeCheckbox
            checked={getAllRootUrls(root).every(url => selected[url])}
            indeterminate={getAllRootUrls(root).some(url => selected[url]) && !getAllRootUrls(root).every(url => selected[url])}
            onChange={e => {
              const allUrls = getAllRootUrls(root);
              const updates: Record<string, boolean> = {};
              for (const url of allUrls) {
                updates[url] = e.target.checked;
              }
              setSelected(prev => ({ ...prev, ...updates }));
            }}
          />
          <span style={{ fontWeight: 600, marginLeft: 4 }}>Select All</span>
          <div style={{ flex: 1 }} />
          <span style={{ display: 'flex', alignItems: 'center', marginLeft: 'auto' }}>
            <input
              type="text"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              placeholder="Search files/folders..."
              style={{ padding: '2px 8px', border: '1px solid #ccc', borderRadius: 4 }}
            />
            <button
              onClick={() => setSearchText(searchInput)}
              style={{ marginLeft: 4, background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}
              title="Search"
            >
              🔍
            </button>
          </span>
        </div>
      )}
      {loading && <div>Loading directory...</div>}
      {!loading && root && selectedSource && (
        <div style={{ maxHeight: 400, overflowY: "auto", border: "1px solid #eee", borderRadius: 4, padding: 8 }}>
          {root.map(node => renderNode(node))}
        </div>
      )}
      <button
        className="mt-4 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        onClick={handleDownloadClick}
        disabled={!root || Object.values(selected).every(v => !v) || !selectedSource}
      >
        Download Selected
      </button>
      {showModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-bold mb-2">Download Confirmation</h3>
            <p className="mb-2">
              You are about to download <b>{modalFiles.length}</b> file(s) with a total size of <b>{formatFileSize(totalSize)}</b>.
            </p>
            <ul className="mb-2 max-h-32 overflow-y-auto text-xs">
              {modalFiles.slice(0, 10).map(f => (
                <li key={f.url}>{f.name} ({formatFileSize(f.size)})</li>
              ))}
              {modalFiles.length > 10 && <li>...and {modalFiles.length - 10} more</li>}
            </ul>
            <div className="flex gap-2 mt-4">
              <button
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                onClick={() => {
                  setShowModal(false);
                  onDownload(modalFiles);
                }}
              >
                Confirm Download
              </button>
              <button
                className="bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500"
                onClick={() => setShowModal(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      {infoModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.3)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 600, maxHeight: '80vh', overflowY: 'auto', boxShadow: '0 2px 16px rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontWeight: 600, fontSize: 18 }}>{infoModalTitle}</span>
              <button onClick={() => setInfoModalOpen(false)} style={{ fontSize: 20, background: 'none', border: 'none', cursor: 'pointer' }}>✖️</button>
            </div>
            {infoModalHtml === '<div>Loading...</div>' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 40 }}>
                <span style={{ display: 'inline-block', width: 24, height: 24 }}>
                  <svg style={{ display: 'block' }} width="24" height="24" viewBox="0 0 50 50">
                    <circle cx="25" cy="25" r="20" fill="none" stroke="#2563eb" strokeWidth="5" strokeDasharray="31.4 31.4" strokeLinecap="round">
                      <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite" />
                    </circle>
                  </svg>
                </span>
                <span>Loading...</span>
              </div>
            ) : (
              <div dangerouslySetInnerHTML={{ __html: infoModalHtml || '<div style=\'color:red\'>No info found or failed to render info.</div>' }} />
            )}
          </div>
        </div>
      )}
      {manualModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.3)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 400, minWidth: 320, boxShadow: '0 2px 16px rgba(0,0,0,0.2)' }}>
            <h3 style={{ fontWeight: 600, fontSize: 18, marginBottom: 16 }}>Add Manual Repository</h3>
            <div style={{ marginBottom: 12 }}>
              <label>Name:</label>
              <input type="text" value={manualName} onChange={e => setManualName(e.target.value)} style={{ width: '100%', padding: 6, marginTop: 2, marginBottom: 8 }} />
              <label>Repository URL:</label>
              <input type="text" value={manualRepoUrl} onChange={e => setManualRepoUrl(e.target.value)} style={{ width: '100%', padding: 6, marginTop: 2, marginBottom: 8 }} />
              <label>Info URL:</label>
              <input type="text" value={manualInfoUrl} onChange={e => setManualInfoUrl(e.target.value)} style={{ width: '100%', padding: 6, marginTop: 2, marginBottom: 8 }} disabled={manualNoInfo} />
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                <input type="checkbox" id="noInfo" checked={manualNoInfo} onChange={e => { setManualNoInfo(e.target.checked); if (e.target.checked) setManualInfoUrl(''); }} />
                <label htmlFor="noInfo" style={{ marginLeft: 6, color: manualNoInfo ? '#888' : undefined }}>No Info URL</label>
              </div>
              {manualError && <div style={{ color: 'red', marginBottom: 8 }}>{manualError}</div>}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={() => setManualModalOpen(false)} style={{ padding: '6px 16px' }}>Cancel</button>
              <button onClick={async () => {
                if (!manualName || !manualRepoUrl) { setManualError('Name and Repository URL are required.'); return; }
                setManualError('');
                // POST to backend
                const resp = await fetch('http://localhost:8080/api/v1/piles/add-source', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ name: manualName, repo_url: manualRepoUrl, info_url: manualNoInfo ? null : manualInfoUrl })
                });
                if (resp.ok) {
                  const updated = await resp.json();
                  setSources(updated);
                  setSelectedSource(manualName);
                  setManualModalOpen(false);
                  setManualName(''); setManualRepoUrl(''); setManualInfoUrl(''); setManualNoInfo(false);
                } else {
                  setManualError('Failed to add source.');
                }
              }} style={{ padding: '6px 16px', background: '#2563eb', color: '#fff', borderRadius: 4 }}>Add</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export function Piles() {
  const [piles, setPiles] = useState<Pile[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<
    "all" | "downloaded" | "downloading" | "pending"
  >("all");
  const [newPile, setNewPile] = useState<Pile>({
    name: "",
    display_name: "",
    description: "",
    category: "general",
    source_type: "kiwix",
    source_url: "",
    tags: [],
  });
  const [validationStatus, setValidationStatus] = useState<
    Record<string, { valid: boolean; message: string; checking: boolean }>
  >({});
  const [showGutenberg, setShowGutenberg] = useState(false);
  const [gutenbergQuery, setGutenbergQuery] = useState("");
  const [gutenbergResults, setGutenbergResults] = useState<GutenbergBook[]>([]);
  const [gutenbergLoading, setGutenbergLoading] = useState(false);

  const handleAddPile = async (e: React.FormEvent) => {
    e.preventDefault();

    console.log("Adding pile:", newPile);

    // First validate the URL
    try {
      const formData = new FormData();
      formData.append("url", newPile.source_url);

      const validationResponse = await fetch(
        "http://localhost:8080/api/v1/piles/validate-url",
        {
          method: "POST",
          body: formData,
        }
      );

      if (validationResponse.ok) {
        const validationResult = await validationResponse.json();

        if (!validationResult.valid) {
          alert(
            `Cannot add pile: ${validationResult.message}\n\nURL: ${newPile.source_url}`
          );
          return;
        }

        // Show file size if available
        if (validationResult.file_size) {
          const sizeMB = (validationResult.file_size / (1024 * 1024)).toFixed(
            1
          );
          const confirmDownload = confirm(
            `This file is ${sizeMB} MB. Do you want to add it to your piles?\n\n` +
              `Note: You can download it later when you're ready.`
          );
          if (!confirmDownload) return;
        }
      } else {
        console.warn("URL validation failed, proceeding anyway...");
      }
    } catch (error) {
      console.warn("URL validation error, proceeding anyway:", error);
    }

    try {
      const response = await fetch("http://localhost:8080/api/v1/piles/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(newPile),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Pile added successfully:", result);
        // Backend returns {success: true, data: {...}}
        const addedPile = result.data;
        setPiles([...piles, addedPile]);
        setNewPile({
          name: "",
          display_name: "",
          description: "",
          category: "general",
          source_type: "kiwix",
          source_url: "",
          tags: [],
        });
        setShowAddForm(false);
        // Reload piles to get updated data
        loadPiles();
        alert(`Pile "${addedPile.display_name}" added successfully!`);
      } else {
        const errorData = await response.json();
        console.error("Failed to add pile:", errorData);
        alert(`Failed to add pile: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error adding pile:", error);
      alert("Error adding pile");
    }
  };

  const handleQuickAdd = async (source: QuickAddSource) => {
    console.log("Quick adding source:", source);

    // First validate the URL
    try {
      const formData = new FormData();
      formData.append("url", source.source_url);

      const validationResponse = await fetch(
        "http://localhost:8080/api/v1/piles/validate-url",
        {
          method: "POST",
          body: formData,
        }
      );

      if (validationResponse.ok) {
        const validationResult = await validationResponse.json();

        if (!validationResult.valid) {
          alert(
            `Cannot add pile: ${validationResult.message}\n\nURL: ${source.source_url}`
          );
          return;
        }

        // Show file size if available
        if (validationResult.file_size) {
          const sizeMB = (validationResult.file_size / (1024 * 1024)).toFixed(
            1
          );
          const confirmDownload = confirm(
            `This file is ${sizeMB} MB. Do you want to add it to your piles?\n\n` +
              `Note: You can download it later when you're ready.`
          );
          if (!confirmDownload) return;
        }
      } else {
        console.warn("URL validation failed, proceeding anyway...");
      }
    } catch (error) {
      console.warn("URL validation error, proceeding anyway:", error);
    }

    try {
      const pileData = {
        name: source.name,
        display_name: source.display_name,
        description: source.description,
        category: source.category,
        source_type: source.source_type,
        source_url: source.source_url,
        tags: source.tags,
      };

      const response = await fetch("http://localhost:8080/api/v1/piles/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(pileData),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Quick add successful:", result);
        const addedPile = result.data;
        setPiles([...piles, addedPile]);
        loadPiles();
        alert(`Pile "${source.display_name}" added successfully!`);
      } else {
        const errorData = await response.json();
        console.error("Failed to quick add:", errorData);
        alert(`Failed to add pile: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error quick adding:", error);
      alert("Error adding pile");
    }
  };

  const handleInputChange = (field: keyof Pile, value: string | string[]) => {
    setNewPile((prev) => ({ ...prev, [field]: value }));
  };

  const loadPiles = async () => {
    try {
      console.log("Loading piles...");
      const response = await fetch("http://localhost:8080/api/v1/piles/");
      if (response.ok) {
        const result = await response.json();
        console.log("Piles loaded:", result);
        // Backend returns {success: true, data: [...]}
        setPiles(result.data || []);
      } else {
        console.error(
          "Failed to load piles:",
          response.status,
          response.statusText
        );
      }
    } catch (error) {
      console.error("Error loading piles:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPiles();
  }, []);

  // Poll for updates every 2 seconds to show real-time download progress
  useEffect(() => {
    const interval = setInterval(() => {
      loadPiles();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const getSourceTypeExamples = (type: string) => {
    switch (type) {
      case "kiwix":
        return [
          "https://download.kiwix.org/zim/wikipedia_en_all.zim",
          "https://download.kiwix.org/zim/medical_en_all.zim",
          "https://download.kiwix.org/zim/gutenberg_en_all.zim",
        ];
      case "http":
        return [
          "https://example.com/file.zip",
          "https://archive.org/download/example.iso",
          "https://files.example.com/document.pdf",
        ];
      case "torrent":
        return ["https://example.com/file.torrent", "magnet:?xt=urn:btih:..."];
      default:
        return [];
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "easy":
        return "bg-green-100 text-green-800";
      case "moderate":
        return "bg-yellow-100 text-yellow-800";
      case "advanced":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case "education":
        return "bg-blue-100 text-blue-800";
      case "medical":
        return "bg-red-100 text-red-800";
      case "books":
        return "bg-purple-100 text-purple-800";
      case "travel":
        return "bg-green-100 text-green-800";
      case "agriculture":
        return "bg-orange-100 text-orange-800";
      case "engineering":
        return "bg-indigo-100 text-indigo-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "-";
    const units = ["B", "KB", "MB", "GB"];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const handleDownload = async (pile: Pile) => {
    if (!pile.id) return;

    // Prevent duplicate downloads
    if (pile.is_downloading) {
      alert("This pile is already being downloaded. Please wait for it to complete.");
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/piles/${pile.id}/download-source`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        const result = await response.json();
        console.log("Download started:", result);
        alert(result.message);
        // Reload piles to get updated status
        loadPiles();
      } else {
        const errorData = await response.json();
        console.error("Download failed:", errorData);
        alert(`Download failed: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error starting download:", error);
      alert("Error starting download");
    }
  };

  const handleDelete = async (pile: Pile) => {
    if (!pile.id) return;

    if (
      !confirm(
        `Are you sure you want to delete "${pile.display_name}"? This will also delete the downloaded file.`
      )
    ) {
      return;
    }

    try {
      const response = await fetch(
        `http://localhost:8080/api/v1/piles/${pile.id}`,
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.ok) {
        const result = await response.json();
        console.log("Pile deleted:", result);
        alert(result.message);
        // Reload piles to update the list
        loadPiles();
      } else {
        const errorData = await response.json();
        console.error("Delete failed:", errorData);
        alert(`Delete failed: ${errorData.detail}`);
      }
    } catch (error) {
      console.error("Error deleting pile:", error);
      alert("Error deleting pile");
    }
  };

  const validateQuickAddUrl = async (sourceId: string, url: string) => {
    if (validationStatus[sourceId]?.checking) return;

    setValidationStatus((prev) => ({
      ...prev,
      [sourceId]: { valid: false, message: "Checking...", checking: true },
    }));

    try {
      const formData = new FormData();
      formData.append("url", url);

      const response = await fetch(
        "http://localhost:8080/api/v1/piles/validate-url",
        {
          method: "POST",
          body: formData,
        }
      );

      if (response.ok) {
        const result = await response.json();
        setValidationStatus((prev) => ({
          ...prev,
          [sourceId]: {
            valid: result.valid,
            message: result.message,
            checking: false,
          },
        }));
      } else {
        setValidationStatus((prev) => ({
          ...prev,
          [sourceId]: {
            valid: false,
            message: "Validation failed",
            checking: false,
          },
        }));
      }
    } catch (error) {
      setValidationStatus((prev) => ({
        ...prev,
        [sourceId]: {
          valid: false,
          message: "Network error",
          checking: false,
        },
      }));
    }
  };

  const searchGutenberg = async () => {
    setGutenbergLoading(true);
    setGutenbergResults([]);
    try {
      const resp = await fetch(
        `http://localhost:8080/api/v1/piles/gutenberg-search?query=${encodeURIComponent(
          gutenbergQuery
        )}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setGutenbergResults(data.data.results || []);
      } else {
        setGutenbergResults([]);
      }
    } catch (e) {
      setGutenbergResults([]);
    } finally {
      setGutenbergLoading(false);
    }
  };

  const handleAddGutenbergPile = async (book: GutenbergBook) => {
    const pileData = {
      name: `gutenberg_${book.id}`,
      display_name: book.title,
      description: `Project Gutenberg book${book.authors && book.authors.length ? ` by ${book.authors.map(a => a.name).join(", ")}` : ""}`,
      category: "books",
      source_type: "gutenberg",
      source_url: String(book.id),
      tags: book.subjects?.slice(0, 5) || [],
    };
    try {
      const response = await fetch("http://localhost:8080/api/v1/piles/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(pileData),
      });
      if (response.ok) {
        const result = await response.json();
        setPiles([...piles, result.data]);
        loadPiles();
        alert(`Pile for '${book.title}' added!`);
      } else {
        const errorData = await response.json();
        alert(`Failed to add pile: ${errorData.detail}`);
      }
    } catch (e) {
      alert("Error adding pile");
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Piles</h1>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowQuickAdd(!showQuickAdd)}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            {showQuickAdd ? "Hide Quick Add" : "Quick Add"}
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            {showAddForm ? "Cancel" : "Add Pile"}
          </button>
        </div>
      </div>

      {showQuickAdd && (
        <KiwixTreeBrowser
          onDownload={async (files) => {
            // For each file, create a pile
            for (const file of files) {
              const pileData = {
                name: file.name.replace(/\W+/g, "_").toLowerCase(),
                display_name: file.name,
                description: `Kiwix ZIM file: ${file.name}`,
                category: "education",
                source_type: "kiwix",
                source_url: file.url,
                tags: ["kiwix", "zim"],
              };
              await fetch("http://localhost:8080/api/v1/piles/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(pileData),
              });
            }
            alert(`Added ${files.length} pile(s) to your library!`);
          }}
        />
      )}

      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Add New Pile
          </h2>
          <form onSubmit={handleAddPile} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name (Internal)
              </label>
              <input
                type="text"
                value={newPile.name}
                onChange={(e) => handleInputChange("name", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., wikipedia_en"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Display Name
              </label>
              <input
                type="text"
                value={newPile.display_name}
                onChange={(e) =>
                  handleInputChange("display_name", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Wikipedia English"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Category
              </label>
              <select
                value={newPile.category}
                onChange={(e) => handleInputChange("category", e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="general">General</option>
                <option value="education">Education</option>
                <option value="medical">Medical</option>
                <option value="books">Books</option>
                <option value="software">Software</option>
                <option value="media">Media</option>
                <option value="travel">Travel</option>
                <option value="agriculture">Agriculture</option>
                <option value="engineering">Engineering</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={newPile.description}
                onChange={(e) =>
                  handleInputChange("description", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Brief description of the content"
                rows={3}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source Type
              </label>
              <select
                value={newPile.source_type}
                onChange={(e) =>
                  handleInputChange(
                    "source_type",
                    e.target.value as "kiwix" | "http" | "torrent"
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="kiwix">Kiwix (ZIM files)</option>
                <option value="http">HTTP/HTTPS</option>
                <option value="torrent">Torrent</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source URL
              </label>
              <input
                type="url"
                value={newPile.source_url}
                onChange={(e) =>
                  handleInputChange("source_url", e.target.value)
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter the download URL"
                required
              />
              <div className="mt-1 text-sm text-gray-500">
                <p className="font-medium">
                  Examples for {newPile.source_type}:
                </p>
                <ul className="list-disc list-inside mt-1">
                  {getSourceTypeExamples(newPile.source_type).map(
                    (example, index) => (
                      <li key={index} className="text-xs">
                        {example}
                      </li>
                    )
                  )}
                </ul>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                value={newPile.tags?.join(", ") || ""}
                onChange={(e) =>
                  handleInputChange(
                    "tags",
                    e.target.value.split(",").map((tag) => tag.trim())
                  )
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="education, wikipedia, offline"
              />
            </div>

            <div className="flex space-x-3">
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Add Pile
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-lg shadow">
        {loading ? (
          <div className="p-6">
            <p className="text-gray-500">Loading piles...</p>
          </div>
        ) : piles.length === 0 ? (
          <div className="p-6">
            <p className="text-gray-500">No piles configured yet.</p>
            <p className="text-sm text-gray-400 mt-2">
              Use "Quick Add" to add popular content sources or "Add Pile" for
              custom sources.
            </p>
          </div>
        ) : (
          <div className="p-6">
            {/* Filter Controls */}
            <div className="mb-6">
              <div className="flex items-center space-x-4">
                <span className="text-sm font-medium text-gray-700">
                  Filter:
                </span>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setFilter("all")}
                    className={`px-3 py-1 text-sm rounded ${
                      filter === "all"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                  >
                    All ({piles.length})
                  </button>
                  <button
                    onClick={() => setFilter("downloaded")}
                    className={`px-3 py-1 text-sm rounded ${
                      filter === "downloaded"
                        ? "bg-green-600 text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                  >
                    Downloaded ({piles.filter((p) => p.file_path).length})
                  </button>
                  <button
                    onClick={() => setFilter("downloading")}
                    className={`px-3 py-1 text-sm rounded ${
                      filter === "downloading"
                        ? "bg-yellow-600 text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                  >
                    Downloading ({piles.filter((p) => p.is_downloading).length})
                  </button>
                  <button
                    onClick={() => setFilter("pending")}
                    className={`px-3 py-1 text-sm rounded ${
                      filter === "pending"
                        ? "bg-gray-600 text-white"
                        : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                    }`}
                  >
                    Pending (
                    {
                      piles.filter((p) => !p.file_path && !p.is_downloading)
                        .length
                    }
                    )
                  </button>
                </div>
              </div>
            </div>

            <div className="grid gap-4">
              {piles
                .filter((pile) => {
                  switch (filter) {
                    case "downloaded":
                      return pile.file_path;
                    case "downloading":
                      return pile.is_downloading;
                    case "pending":
                      return !pile.file_path && !pile.is_downloading;
                    default:
                      return true;
                  }
                })
                .map((pile, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          {pile.display_name}
                        </h3>
                        <p className="text-sm text-gray-500">{pile.name}</p>
                        <p className="text-sm text-gray-600 mt-1">
                          {pile.description}
                        </p>
                        <div className="flex items-center mt-2 space-x-2">
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
                          <span
                            className={`px-2 py-1 text-xs rounded ${getCategoryColor(
                              pile.category
                            )}`}
                          >
                            {pile.category}
                          </span>
                          {pile.tags &&
                            pile.tags.map((tag, tagIndex) => (
                              <span
                                key={tagIndex}
                                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
                              >
                                {tag}
                              </span>
                            ))}
                        </div>

                        {/* Status and Progress */}
                        <div className="mt-2">
                          {pile.is_downloading ? (
                            <div className="flex items-center space-x-2">
                              <span className="text-xs text-blue-600">
                                Downloading...
                              </span>
                              <div className="w-24 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                  style={{
                                    width: `${
                                      (pile.download_progress || 0) * 100
                                    }%`,
                                  }}
                                ></div>
                              </div>
                              <span className="text-xs text-gray-600">
                                {Math.round(
                                  (pile.download_progress || 0) * 100
                                )}
                                %
                              </span>
                            </div>
                          ) : pile.file_path ? (
                            <div className="flex items-center space-x-2">
                              <span className="text-xs text-green-600">
                                ✓ Downloaded
                              </span>
                              {pile.file_size && (
                                <span className="text-xs text-gray-600">
                                  {formatFileSize(pile.file_size)}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-gray-600">
                              Not downloaded
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleDownload(pile)}
                          disabled={pile.is_downloading}
                          className={`text-sm ${
                            pile.is_downloading
                              ? "text-gray-400 cursor-not-allowed"
                              : "text-blue-600 hover:text-blue-800"
                          }`}
                        >
                          {pile.is_downloading ? "Downloading..." : "Download"}
                        </button>
                        <button
                          onClick={() => handleDelete(pile)}
                          className="text-red-600 hover:text-red-800 text-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
