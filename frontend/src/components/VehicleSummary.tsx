import { useStore } from '../store/useStore'

const ORDER = ['car', 'truck', 'bus', 'van', 'motorcycle', 'bicycle', 'other']

export default function VehicleSummary() {
  const { vehicles, status } = useStore()
  const counts: Record<string, number> = {}
  for (const v of vehicles) counts[v.class_name] = (counts[v.class_name] || 0) + 1
  const total = vehicles.length
  const unit = vehicles[0]?.speed_unit || (status ? 'px/s' : 'px/s')

  return (
    <div className="panel p-4">
      <div className="panel-title mb-3">Vehicle Summary</div>
      {!status && <div className="text-sm text-[#8fa3c8]">Start analysis to see live counts.</div>}
      <div className="space-y-1.5 text-sm">
        {ORDER.filter((c) => counts[c]).map((c) => (
          <div key={c} className="flex justify-between items-center">
            <span className="capitalize text-[#c7d4ee]">{c}s</span>
            <span className="font-mono font-bold text-lg">{counts[c]}</span>
          </div>
        ))}
        <div className="flex justify-between items-center pt-2 border-t border-[#24365e]">
          <span className="font-bold">Total</span>
          <span className="font-mono font-black text-2xl text-blue-300">{total}</span>
        </div>
      </div>
      <div className="mt-3 text-[11px] text-[#8fa3c8]">
        Speed unit: <span className="font-mono text-[#c7d4ee]">{unit}</span>
        {unit === 'px/s' && <span> (pixel units — calibrate for km/h)</span>}
      </div>
      {!status?.model_loaded && status && (
        <div className="mt-2 p-2 rounded bg-amber-950/60 border border-amber-800 text-[11px] text-amber-200">
          MODEL NOT AVAILABLE — install ultralytics + weights for real detection.
        </div>
      )}
    </div>
  )
}
