import { useStore } from '../store/useStore'

function fmt(t: number) {
  const m = Math.floor(t / 60), s = Math.floor(t % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function EventFeed({ compact = false }: { compact?: boolean }) {
  const { events } = useStore()
  const list = compact ? events.slice(-12).reverse() : [...events].reverse()

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="panel-title mb-3">Events &amp; Alerts</div>
      <div className={`flex-1 overflow-y-auto space-y-2 ${compact ? 'max-h-64' : ''}`}>
        {list.length === 0 && <div className="text-sm text-[#8fa3c8]">No events yet — rules fire only from real backend state.</div>}
        {list.map((e, i) => (
          <div key={i} className={`ev-${e.severity} border-l-4 pl-3 py-1.5 pr-2 rounded-r bg-[#0d1530]/70`}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold">{e.event_type}</span>
              <span className="font-mono text-[#8fa3c8]">{fmt(e.timestamp)}</span>
            </div>
            <div className="text-xs text-[#8fa3c8]">{e.description}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
