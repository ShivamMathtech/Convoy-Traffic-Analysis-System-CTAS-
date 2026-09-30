import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { sessionsApi } from '../services/api'
import { useStore } from '../store/useStore'
import type { SessionMeta } from '../types'

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionMeta[]>([])
  const { setSession } = useStore()

  const load = () => sessionsApi.list().then((d) => setSessions(d.sessions || [])).catch(() => {})
  useEffect(() => { load() }, [])

  const remove = async (id: string) => {
    if (!confirm('Delete session and all its outputs?')) return
    await sessionsApi.remove(id)
    load()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Session History</h1>
      <div className="panel overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-[#8fa3c8] border-b border-[#1e2f5c]">
              <th className="p-3">Session</th><th className="p-3">Source</th><th className="p-3">Date</th>
              <th className="p-3">Vehicles</th><th className="p-3">Events</th><th className="p-3">Status</th><th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-b border-[#131f45] hover:bg-[#101b3a]">
                <td className="p-3 font-mono text-xs">{s.name || s.id}</td>
                <td className="p-3 text-xs">{s.source_type}</td>
                <td className="p-3 text-xs text-[#8fa3c8]">{s.started_at?.slice(0, 16).replace('T', ' ') || '—'}</td>
                <td className="p-3 font-mono">{s.vehicles ?? '—'}</td>
                <td className="p-3 font-mono">{s.events ?? '—'}</td>
                <td className="p-3"><span className="text-xs px-2 py-0.5 rounded bg-[#16224a] border border-[#24365e]">{s.status}</span></td>
                <td className="p-3">
                  <div className="flex gap-2">
                    <button className="btn btn-ghost !py-1 !px-2 !text-xs" onClick={() => setSession(s.id)}>Open</button>
                    <Link className="btn btn-ghost !py-1 !px-2 !text-xs" to="/reports">Report</Link>
                    <button className="btn btn-danger !py-1 !px-2 !text-xs" onClick={() => remove(s.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr><td colSpan={7} className="p-6 text-center text-sm text-[#8fa3c8]">No sessions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
