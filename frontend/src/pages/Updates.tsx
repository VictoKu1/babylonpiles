import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = 'http://localhost:8080/api/v1'

interface MirrorVariantCatalog {
  variant: string
  display_name: string
  description: string
  destination_subpath: string
}

interface MirrorProviderCatalog {
  provider: string
  display_name: string
  description: string
  variants: MirrorVariantCatalog[]
}

interface MirrorRun {
  id: number
  job_id: number
  status: string
  started_at: string | null
  finished_at: string | null
  exit_code: number | null
  bytes_downloaded: number
  log_path: string | null
  error_message: string | null
}

interface MirrorJob {
  id: number
  provider: string
  variant: string
  destination_subpath: string
  enabled: boolean
  schedule_enabled: boolean
  schedule_frequency: 'disabled' | 'daily' | 'weekly' | 'monthly'
  schedule_time_utc: string
  schedule_day: number | null
  status: string
  last_run_at: string | null
  next_run_at: string | null
  last_error: string | null
  latest_run: MirrorRun | null
}

interface MirrorJobDraft {
  enabled: boolean
  schedule_enabled: boolean
  schedule_frequency: 'disabled' | 'daily' | 'weekly' | 'monthly'
  schedule_time_utc: string
  schedule_day: number | null
}

const WEEKDAY_OPTIONS = [
  { value: 0, label: 'Sunday' },
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' },
]

function bytesToHuman(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}

function formatDate(value: string | null) {
  if (!value) return 'Not scheduled'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return `${parsed.toLocaleDateString()} ${parsed.toLocaleTimeString()}`
}

function buildDraft(job: MirrorJob): MirrorJobDraft {
  return {
    enabled: job.enabled,
    schedule_enabled: job.schedule_enabled,
    schedule_frequency: job.schedule_frequency,
    schedule_time_utc: job.schedule_time_utc,
    schedule_day: job.schedule_day,
  }
}

export function Updates() {
  const [providers, setProviders] = useState<MirrorProviderCatalog[]>([])
  const [jobs, setJobs] = useState<MirrorJob[]>([])
  const [drafts, setDrafts] = useState<Record<number, MirrorJobDraft>>({})
  const [logExcerpts, setLogExcerpts] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [savingJobId, setSavingJobId] = useState<number | null>(null)
  const [runningJobId, setRunningJobId] = useState<number | null>(null)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedVariant, setSelectedVariant] = useState('')

  const providerMap = useMemo(() => {
    return Object.fromEntries(providers.map((provider) => [provider.provider, provider]))
  }, [providers])

  const selectedProviderCatalog = useMemo(
    () => providers.find((provider) => provider.provider === selectedProvider) || null,
    [providers, selectedProvider]
  )

  const selectedVariantCatalog = useMemo(
    () =>
      selectedProviderCatalog?.variants.find((variant) => variant.variant === selectedVariant) || null,
    [selectedProviderCatalog, selectedVariant]
  )

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    if (!providers.length) return
    if (!selectedProvider) {
      setSelectedProvider(providers[0].provider)
      setSelectedVariant(providers[0].variants[0]?.variant || '')
    }
  }, [providers, selectedProvider])

  useEffect(() => {
    if (!selectedProviderCatalog) return
    const validVariants = selectedProviderCatalog.variants.map((variant) => variant.variant)
    if (!validVariants.includes(selectedVariant)) {
      setSelectedVariant(validVariants[0] || '')
    }
  }, [selectedProviderCatalog, selectedVariant])

  useEffect(() => {
    const latestRunIds = jobs
      .map((job) => job.latest_run?.id || null)
      .filter((runId): runId is number => runId !== null)

    if (!latestRunIds.length) {
      setLogExcerpts({})
      return
    }

    void Promise.all(
      latestRunIds.map(async (runId) => {
        try {
          const response = await fetch(`${API_BASE}/mirrors/runs/${runId}/logs?tail=20`)
          if (!response.ok) {
            return [runId, '']
          }
          const payload = await response.json()
          return [runId, payload.data?.content || '']
        } catch {
          return [runId, '']
        }
      })
    ).then((entries) => {
      setLogExcerpts(Object.fromEntries(entries))
    })
  }, [jobs])

  async function loadData() {
    setLoading(true)
    try {
      const [providersResponse, jobsResponse] = await Promise.all([
        fetch(`${API_BASE}/mirrors/providers`),
        fetch(`${API_BASE}/mirrors/jobs`),
      ])

      if (!providersResponse.ok || !jobsResponse.ok) {
        throw new Error('Failed to load mirrored source data')
      }

      const providersPayload = await providersResponse.json()
      const jobsPayload = await jobsResponse.json()
      const nextJobs: MirrorJob[] = jobsPayload.data || []

      setProviders(providersPayload.data || [])
      setJobs(nextJobs)
      setDrafts(
        Object.fromEntries(nextJobs.map((job) => [job.id, buildDraft(job)]))
      )
    } catch (error) {
      window.alert('Failed to load mirrored sources.')
    } finally {
      setLoading(false)
    }
  }

  function updateDraft(jobId: number, patch: Partial<MirrorJobDraft>) {
    setDrafts((current) => ({
      ...current,
      [jobId]: {
        ...(current[jobId] || {
          enabled: true,
          schedule_enabled: false,
          schedule_frequency: 'disabled',
          schedule_time_utc: '02:00',
          schedule_day: null,
        }),
        ...patch,
      },
    }))
  }

  async function handleCreateJob(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedProvider || !selectedVariant) return

    try {
      const response = await fetch(`${API_BASE}/mirrors/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          variant: selectedVariant,
          enabled: true,
          schedule_enabled: false,
          schedule_frequency: 'disabled',
          schedule_time_utc: '02:00',
          schedule_day: null,
        }),
      })

      if (!response.ok) {
        const payload = await response.json()
        window.alert(payload.detail || 'Failed to create mirrored source job.')
        return
      }

      await loadData()
    } catch {
      window.alert('Failed to create mirrored source job.')
    }
  }

  async function handleSaveJob(jobId: number) {
    const draft = drafts[jobId]
    if (!draft) return

    setSavingJobId(jobId)
    try {
      const response = await fetch(`${API_BASE}/mirrors/jobs/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })

      if (!response.ok) {
        const payload = await response.json()
        window.alert(payload.detail || 'Failed to save mirror job.')
        return
      }

      await loadData()
    } catch {
      window.alert('Failed to save mirror job.')
    } finally {
      setSavingJobId(null)
    }
  }

  async function handleRunJob(jobId: number) {
    setRunningJobId(jobId)
    try {
      const response = await fetch(`${API_BASE}/mirrors/jobs/${jobId}/run`, {
        method: 'POST',
      })

      if (!response.ok) {
        const payload = await response.json()
        window.alert(payload.detail || 'Failed to queue mirror run.')
        return
      }

      await loadData()
    } catch {
      window.alert('Failed to queue mirror run.')
    } finally {
      setRunningJobId(null)
    }
  }

  const configuredJobKeys = new Set(jobs.map((job) => `${job.provider}:${job.variant}`))
  const selectedCombinationConfigured =
    !!selectedProvider && !!selectedVariant && configuredJobKeys.has(`${selectedProvider}:${selectedVariant}`)
  const remainingVariants = providers.flatMap((provider) =>
    provider.variants
      .filter((variant) => !configuredJobKeys.has(`${provider.provider}:${variant.variant}`))
      .map((variant) => ({ provider, variant }))
  )

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Updates</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure vendored EmergencyStorage mirror jobs and scheduled sync windows in UTC.
          </p>
        </div>
        <button
          onClick={() => void loadData()}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Add Mirrored Source</h2>
        <p className="text-sm text-gray-500 mb-4">
          Each provider/variant pair can be configured once and writes into the shared piles volume.
        </p>

        <form onSubmit={handleCreateJob} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={selectedProvider}
              onChange={(event) => setSelectedProvider(event.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              {providers.map((provider) => (
                <option key={provider.provider} value={provider.provider}>
                  {provider.display_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Variant</label>
            <select
              value={selectedVariant}
              onChange={(event) => setSelectedVariant(event.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              {(selectedProviderCatalog?.variants || []).map((variant) => (
                <option key={variant.variant} value={variant.variant}>
                  {variant.display_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Destination Preview</label>
            <div className="w-full px-3 py-2 border border-gray-200 bg-gray-50 rounded-md text-sm text-gray-700">
              {selectedVariantCatalog
                ? `/mnt/babylonpiles/piles/${selectedVariantCatalog.destination_subpath}`
                : 'Select a variant'}
            </div>
          </div>

          <button
            type="submit"
            disabled={!selectedVariantCatalog || selectedCombinationConfigured}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
          >
            Add Mirror Job
          </button>
        </form>

        {selectedProviderCatalog && (
          <div className="mt-4 text-sm text-gray-600">
            <p className="font-medium text-gray-800">{selectedProviderCatalog.display_name}</p>
            <p>{selectedVariantCatalog?.description || selectedProviderCatalog.description}</p>
          </div>
        )}

        {remainingVariants.length === 0 && (
          <p className="mt-4 text-sm text-green-700">
            All supported mirrored sources are already configured.
          </p>
        )}
        {selectedCombinationConfigured && (
          <p className="mt-4 text-sm text-amber-700">
            This provider/variant pair is already configured below.
          </p>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Mirrored Sources</h2>

        {loading ? (
          <p className="text-gray-500">Loading mirrored sources...</p>
        ) : jobs.length === 0 ? (
          <p className="text-gray-500">No mirror jobs configured yet.</p>
        ) : (
          <div className="space-y-6">
            {jobs.map((job) => {
              const draft = drafts[job.id] || buildDraft(job)
              const provider = providerMap[job.provider]
              const variant = provider?.variants.find((item) => item.variant === job.variant)
              const latestRun = job.latest_run
              const latestLog = latestRun ? logExcerpts[latestRun.id] || '' : ''

              return (
                <div key={job.id} className="border border-gray-200 rounded-lg p-5">
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">
                        {provider?.display_name || job.provider} / {variant?.display_name || job.variant}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {variant?.description || provider?.description}
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        Destination: /mnt/babylonpiles/piles/{job.destination_subpath}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <span
                        className={`px-2 py-1 text-xs rounded ${
                          job.status === 'running'
                            ? 'bg-yellow-100 text-yellow-800'
                            : job.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : job.status === 'failed'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {job.status.toUpperCase()}
                      </span>
                      {!job.enabled && (
                        <span className="px-2 py-1 text-xs rounded bg-gray-200 text-gray-700">
                          DISABLED
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={draft.enabled}
                        onChange={(event) => updateDraft(job.id, { enabled: event.target.checked })}
                      />
                      Enabled
                    </label>

                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={draft.schedule_enabled}
                        onChange={(event) =>
                          updateDraft(job.id, {
                            schedule_enabled: event.target.checked,
                            schedule_frequency: event.target.checked
                              ? draft.schedule_frequency === 'disabled'
                                ? 'daily'
                                : draft.schedule_frequency
                              : 'disabled',
                            schedule_day: event.target.checked ? draft.schedule_day : null,
                          })
                        }
                      />
                      Schedule Enabled
                    </label>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Frequency</label>
                      <select
                        value={draft.schedule_frequency}
                        onChange={(event) =>
                          updateDraft(job.id, {
                            schedule_frequency: event.target.value as MirrorJobDraft['schedule_frequency'],
                            schedule_day:
                              event.target.value === 'weekly'
                                ? draft.schedule_day ?? 0
                                : event.target.value === 'monthly'
                                ? draft.schedule_day ?? 1
                                : null,
                          })
                        }
                        disabled={!draft.schedule_enabled}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-100"
                      >
                        {!draft.schedule_enabled && <option value="disabled">Disabled</option>}
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Time (UTC)</label>
                      <input
                        type="time"
                        value={draft.schedule_time_utc}
                        onChange={(event) => updateDraft(job.id, { schedule_time_utc: event.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      />
                    </div>

                    <div>
                      {draft.schedule_enabled && draft.schedule_frequency === 'weekly' ? (
                        <>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Day</label>
                          <select
                            value={draft.schedule_day ?? 0}
                            onChange={(event) =>
                              updateDraft(job.id, { schedule_day: Number(event.target.value) })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          >
                            {WEEKDAY_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </>
                      ) : draft.schedule_enabled && draft.schedule_frequency === 'monthly' ? (
                        <>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Day of Month</label>
                          <input
                            type="number"
                            min={1}
                            max={31}
                            value={draft.schedule_day ?? 1}
                            onChange={(event) =>
                              updateDraft(job.id, { schedule_day: Number(event.target.value) })
                            }
                            className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          />
                        </>
                      ) : (
                        <>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Day</label>
                          <div className="w-full px-3 py-2 border border-gray-200 bg-gray-50 rounded-md text-sm text-gray-500">
                            Not required
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-3 mb-5">
                    <button
                      onClick={() => void handleSaveJob(job.id)}
                      disabled={savingJobId === job.id}
                      className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
                    >
                      {savingJobId === job.id ? 'Saving...' : 'Save Settings'}
                    </button>
                    <button
                      onClick={() => void handleRunJob(job.id)}
                      disabled={runningJobId === job.id || job.status === 'running' || !draft.enabled}
                      className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
                    >
                      {job.status === 'running'
                        ? 'Running...'
                        : runningJobId === job.id
                        ? 'Queueing...'
                        : 'Run Now'}
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                    <div className="bg-gray-50 rounded p-3">
                      <p className="text-gray-500">Last Run</p>
                      <p className="font-medium text-gray-900">{formatDate(job.last_run_at)}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-3">
                      <p className="text-gray-500">Next Scheduled Run</p>
                      <p className="font-medium text-gray-900">{formatDate(job.next_run_at)}</p>
                    </div>
                    <div className="bg-gray-50 rounded p-3">
                      <p className="text-gray-500">Latest Run Status</p>
                      <p className="font-medium text-gray-900">
                        {latestRun ? latestRun.status.toUpperCase() : 'No runs yet'}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded p-3">
                      <p className="text-gray-500">Latest Bytes Written</p>
                      <p className="font-medium text-gray-900">
                        {latestRun ? bytesToHuman(latestRun.bytes_downloaded) : '0 B'}
                      </p>
                    </div>
                  </div>

                  {(job.last_error || latestLog) && (
                    <div className="mt-4">
                      <div className="flex justify-between items-center mb-2">
                        <h4 className="text-sm font-semibold text-gray-800">Recent Log Excerpt</h4>
                        {latestRun?.exit_code !== null && latestRun?.exit_code !== undefined && (
                          <span className="text-xs text-gray-500">Exit code: {latestRun.exit_code}</span>
                        )}
                      </div>

                      {job.last_error && (
                        <p className="text-sm text-red-700 mb-2">{job.last_error}</p>
                      )}

                      <pre className="bg-gray-900 text-gray-100 text-xs rounded p-3 overflow-x-auto whitespace-pre-wrap">
                        {latestLog || 'No log output available yet.'}
                      </pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
