import React from 'react'

export interface SourceMetadata {
  found: boolean
  title?: string
  description?: string
  language?: string
  creator?: string
  publisher?: string
}

export function SourceInfo({ info }: { info: SourceMetadata | null }) {
  if (info?.found !== true) return <p className="text-gray-600">No information found.</p>

  const fields = [
    ['Title', info.title],
    ['Description', info.description],
    ['Language', info.language],
    ['Creator', info.creator],
    ['Publisher', info.publisher],
  ]

  return (
    <div className="leading-relaxed break-words">
      {fields.map(([label, value]) => (
        <div key={label}><b>{label}:</b> <span className="whitespace-pre-wrap">{typeof value === 'string' ? value : ''}</span></div>
      ))}
    </div>
  )
}
