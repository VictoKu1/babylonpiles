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
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Quick Add - Popular Content Sources
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Add popular offline content repositories with one click. These are
            curated sources that work well with BabylonPiles.
          </p>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {QUICK_ADD_SOURCES.map((source) => (
              <div
                key={source.id}
                className="border rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium text-gray-900 text-sm">
                    {source.display_name}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-1 text-xs rounded ${getDifficultyColor(
                        source.difficulty
                      )}`}
                    >
                      {source.difficulty}
                    </span>
                    {validationStatus[source.id] && (
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          validationStatus[source.id].checking
                            ? "bg-blue-100 text-blue-800"
                            : validationStatus[source.id].valid
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                        title={validationStatus[source.id].message}
                      >
                        {validationStatus[source.id].checking
                          ? "Checking..."
                          : validationStatus[source.id].valid
                          ? "✓ Valid"
                          : "✗ Invalid"}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                  {source.description}
                </p>

                <div className="flex items-center space-x-2 mb-3">
                  <span
                    className={`px-2 py-1 text-xs rounded ${getCategoryColor(
                      source.category
                    )}`}
                  >
                    {source.category}
                  </span>
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                    {source.source_type.toUpperCase()}
                  </span>
                  {source.size && (
                    <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                      {source.size}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-1 mb-3">
                  {source.tags.slice(0, 3).map((tag, index) => (
                    <span
                      key={index}
                      className="px-1 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                    >
                      {tag}
                    </span>
                  ))}
                  {source.tags.length > 3 && (
                    <span className="px-1 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                      +{source.tags.length - 3}
                    </span>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      validateQuickAddUrl(source.id, source.source_url)
                    }
                    className="flex-1 bg-gray-500 text-white px-3 py-2 rounded text-sm hover:bg-gray-600 transition-colors"
                  >
                    Check URL
                  </button>
                  <button
                    onClick={() => handleQuickAdd(source)}
                    className="flex-1 bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700 transition-colors"
                  >
                    Add to Piles
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
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
