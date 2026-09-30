import { useEffect, useState } from 'react'
import { useStore } from '../store/useStore'
import { useSession } from '../hooks/useSessionSocket'
import { sessionsApi } from '../services/api'
import SourceSelector from '../components/SourceSelector'
import VideoPanel from '../components/VideoPanel'
import CalibrationPanel from '../components/CalibrationPanel'
import type { Vehicle } from '../types'

function VehicleDrawer({ v, onClose }: { v: Vehicle; onClose: () => void }) {
  return (
    <div className="fixed right-0 top-0 h-full w-80 z-40 panel !rounded-none p-5 overflow-y-auto border-l border-[#1e2f5c]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold">Vehicle ID {v.track_id}</h3>
        <button className="btn btn-ghost" onClick={onClose}>✕</button>
      </div>
      <dl className="text-sm space-y-2">
        {[['Class', v.class_name], ['Confidence', v.confidence.toFixed(3)],
          ['Speed', v.speed != null ? `${v.speed.toFixed(1)} ${v.speed_unit || ''}` : '—'],
          ['Heading', v.heading != null ? `${v.heading.toFixed(1)}°` : '—'],
          ['Lane', v.lane || '—'], ['Group', v.group_id ?? '—'],
          ['Centroid', `${v.centroid[0].toFixed(0)}, ${v.centroid[1].toFixed(0)}`],
          ['BBox', v.bbox.map((x) => x.toFixed(0)).join(', ')]].map(([k, val]) => (
          <div key={k} className="flex justify-between border-b border-[#16224a] pb-1">
            <dt className="text-[#8fa3c8]">{k}</dt><dd className="font-mono">{val}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default function LiveView() {
  const { sessionId, vehicles } = useStore()
  const [sel, setSel] = useState<Vehicle | null>(null)
  const [filter, setFilter] = useState('')
  useSession(sessionId)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!sessionId) return
      if (e.code === 'Space') { e.preventDefault(); /* handled by VideoPanel buttons */ }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [sessionId])

  const list = vehicles.filter((v) =>
    !filter || v.class_name.includes(filter.toLowerCase()) || String(v.track_id) === filter)

  return (
    <>
      <SourceSelector />
      {sel && <VehicleDrawer v={sel} onClose={() => setSel(null)} />}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-8"><VideoPanel /></div>
        <div className="col-span-12 xl:col-span-4 space-y-4">
          <div className="panel p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="panel-title">Tracked Vehicles ({list.length})</span>
              <input className="input !w-40" placeholder="filter class / id" value={filter} onChange={(e) => setFilter(e.target.value)} />
            </div>
            <div className="max-h-72 overflow-y-auto space-y-1">
              {list.map((v) => (
                <button key={v.track_id} onClick={() => setSel(v)}
                  className="w-full text-left px-3 py-1.5 rounded bg-[#0d1530] hover:bg-[#16224a] border border-[#1c2c5c] text-xs font-mono flex justify-between">
                  <span>ID {v.track_id} · {v.class_name}</span>
                  <span className="text-[#8fa3c8]">{v.speed != null ? `${v.speed.toFixed(1)} ${v.speed_unit || ''}` : ''} {v.lane || ''}</span>
                </button>
              ))}
              {list.length === 0 && <div className="text-xs text-[#8fa3c8]">No vehicles tracked yet.</div>}
            </div>
          </div>
          <CalibrationPanel />
        </div>
      </div>
    </>
  )
}
