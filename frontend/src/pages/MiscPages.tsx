import { useStore } from '../store/useStore'
import { useSession } from '../hooks/useSessionSocket'
import ChartsPanel from '../components/ChartsPanel'
import Map2DView from '../components/Map2DView'
import View3D from '../components/View3D'

export function AnalyticsPage() {
  const { sessionId, analytics } = useStore()
  useSession(sessionId)
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Analytics</h1>
      {!sessionId && <div className="text-sm text-[#8fa3c8]">Start an analysis session to populate charts.</div>}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            ['Total entered', analytics.total_entered],
            ['Speed unit', analytics.unit || 'px'],
            ['Calibrated', analytics.calibrated ? 'yes' : 'no'],
            ['Series points', analytics.vehicle_count_over_time.length],
          ].map(([k, v]) => (
            <div key={k as string} className="panel p-3">
              <div className="text-[11px] text-[#8fa3c8] uppercase tracking-wider">{k}</div>
              <div className="text-xl font-bold font-mono">{String(v)}</div>
            </div>
          ))}
        </div>
      )}
      <ChartsPanel />
    </div>
  )
}

export function MapPage() {
  const { sessionId } = useStore()
  useSession(sessionId)
  return (
    <div className="h-[calc(100vh-7rem)]">
      <Map2DView height="100%" />
    </div>
  )
}

export function View3DPage() {
  const { sessionId } = useStore()
  useSession(sessionId)
  return <View3D height={560} />
}
