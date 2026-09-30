import { useEffect, useState } from 'react'
import { sessionsApi } from '../services/api'
import { useStore } from '../store/useStore'
import EventFeed from '../components/EventFeed'

export default function EventsPage() {
  const { sessionId, setEvents } = useStore()
  const [sev, setSev] = useState('ALL')
  const [q, setQ] = useState('')

  useEffect(() => {
    if (sessionId) sessionsApi.events(sessionId).then((d) => setEvents(d.events || [])).catch(() => {})
  }, [sessionId])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold">Events</h1>
        <select className="select !w-40" value={sev} onChange={(e) => setSev(e.target.value)}>
          {['ALL', 'INFO', 'LOW', 'MEDIUM', 'HIGH'].map((s) => <option key={s}>{s}</option>)}
        </select>
        <input className="input !w-64" placeholder="search type / description" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <FilteredFeed sev={sev} q={q} />
    </div>
  )
}

function FilteredFeed({ sev, q }: { sev: string; q: string }) {
  const { events } = useStore()
  const list = [...events].reverse().filter(
    (e) => (sev === 'ALL' || e.severity === sev) &&
      (!q || (e.event_type + e.description).toLowerCase().includes(q.toLowerCase())),
  )
  return (
    <div className="panel p-4">
      <div className="text-sm text-[#8fa3c8] mb-3">{list.length} events</div>
      <div className="space-y-2 max-h-[70vh] overflow-y-auto">
        {list.map((e, i) => (
          <div key={i} className={`ev-${e.severity} border-l-4 pl-3 py-1.5 pr-2 rounded-r bg-[#0d1530]/70`}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold">{e.event_type} <span className="font-normal text-[#8fa3c8]">[{e.severity}]</span></span>
              <span className="font-mono text-[#8fa3c8]">{e.timestamp.toFixed(1)}s{e.track_id != null ? ` · ID ${e.track_id}` : ''}</span>
            </div>
            <div className="text-xs text-[#8fa3c8]">{e.description}</div>
          </div>
        ))}
        {list.length === 0 && <div className="text-sm text-[#8fa3c8]">No matching events.</div>}
      </div>
    </div>
  )
}
