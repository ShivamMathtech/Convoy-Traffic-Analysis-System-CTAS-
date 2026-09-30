import { useState } from 'react'
import { reportsApi } from '../services/api'
import { useStore } from '../store/useStore'

export default function ReportsPage() {
  const { sessionId } = useStore()
  const [info, setInfo] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const build = async () => {
    if (!sessionId) return
    setBusy(true); setError('')
    try {
      const r = await reportsApi.build(sessionId)
      setInfo(r)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Report generation failed')
    } finally { setBusy(false) }
  }

  const formats: [string, string][] = [
    ['pdf', 'PDF report'], ['json', 'JSON summary'], ['video', 'Annotated video'],
    ['tracks', 'Tracks CSV'], ['detections', 'Detections CSV'],
    ['events', 'Events CSV'], ['analytics', 'Analytics CSV'],
  ]

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-xl font-bold">Reports &amp; Export</h1>
      {!sessionId && <div className="text-sm text-[#8fa3c8]">Select or open a session first.</div>}
      {sessionId && (
        <>
          <div className="panel p-4">
            <div className="text-sm mb-3">Session <span className="font-mono">{sessionId}</span></div>
            <button className="btn btn-primary" disabled={busy} onClick={build}>
              {busy ? 'Generating…' : '📄 Generate Report'}
            </button>
            {error && <div className="mt-2 text-sm text-red-300">{error}</div>}
          </div>
          {info && (
            <div className="panel p-4">
              <div className="panel-title mb-3">Downloads</div>
              <div className="grid grid-cols-2 gap-2">
                {formats.map(([fmt, label]) => (
                  <a key={fmt} className="btn btn-ghost justify-start" href={reportsApi.downloadUrl(sessionId, fmt)} download>
                    ⬇ {label}
                  </a>
                ))}
              </div>
              <div className="mt-3 text-xs text-[#8fa3c8]">
                Output files: {(info.files || []).join(', ')}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
