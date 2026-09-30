import { useEffect, useState } from 'react'
import { settingsApi } from '../services/api'

function Num({ label, value, onChange, step = 1, min, max }: any) {
  return (
    <label className="block">
      <span className="text-xs text-[#8fa3c8]">{label}</span>
      <input type="number" className="input mt-1" value={value ?? ''} step={step} min={min} max={max}
        onChange={(e) => onChange(parseFloat(e.target.value))} />
    </label>
  )
}
function Sel({ label, value, options, onChange }: any) {
  return (
    <label className="block">
      <span className="text-xs text-[#8fa3c8]">{label}</span>
      <select className="select mt-1" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o: string) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  )
}
function Tog({ label, value, onChange }: any) {
  return (
    <label className="flex items-center justify-between py-1 text-sm">
      <span className="text-[#c7d4ee]">{label}</span>
      <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} className="w-4 h-4 accent-blue-500" />
    </label>
  )
}

export default function SettingsForm() {
  const [s, setS] = useState<any>(null)
  const [msg, setMsg] = useState('')
  const [perf, setPerf] = useState<any>(null)

  useEffect(() => {
    settingsApi.get().then(setS).catch(() => {})
    settingsApi.performance().then(setPerf).catch(() => {})
  }, [])

  if (!s) return <div className="text-sm text-[#8fa3c8]">Loading settings…</div>
  const set = (path: string[], v: any) => {
    setS((prev: any) => {
      const next = JSON.parse(JSON.stringify(prev))
      let o = next
      for (let i = 0; i < path.length - 1; i++) o = o[path[i]]
      o[path[path.length - 1]] = v
      return next
    })
  }
  const save = async () => {
    try { await settingsApi.update(s); setMsg('Saved ✓') } catch { setMsg('Save failed') }
    setTimeout(() => setMsg(''), 3000)
  }

  const m = s.model, t = s.tracker, v = s.video, g = s.groups, e = s.events, u = s.ui

  return (
    <div className="space-y-4">
      {perf && (
        <div className="panel p-4">
          <div className="panel-title mb-2">Performance</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>CPU <b className="font-mono">{perf.cpu_percent}%</b></div>
            <div>RAM <b className="font-mono">{perf.ram_percent}%</b></div>
            <div>Disk free <b className="font-mono">{perf.disk_free_gb} GB</b></div>
            <div>GPU <b className="font-mono">{perf.gpu.available ? perf.gpu.name : 'n/a'}</b></div>
            <div>Model <b className="font-mono">{perf.detector.loaded ? 'loaded' : 'NOT AVAILABLE'}</b></div>
            <div>Latency <b className="font-mono">{perf.detector.latency_ms} ms</b></div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="panel p-4 space-y-3">
          <div className="panel-title">Model</div>
          <Sel label="Device" value={m.device} options={['cpu', 'cuda', 'mps']} onChange={(x: string) => set(['model', 'device'], x)} />
          <Sel label="Image size" value={String(m.imgsz)} options={['320', '416', '512', '640', '768', '960']} onChange={(x: string) => set(['model', 'imgsz'], parseInt(x))} />
          <Num label="Confidence threshold" value={m.conf} step={0.05} min={0} max={1} onChange={(x: number) => set(['model', 'conf'], x)} />
          <Num label="IoU threshold" value={m.iou} step={0.05} min={0} max={1} onChange={(x: number) => set(['model', 'iou'], x)} />
          <label className="block"><span className="text-xs text-[#8fa3c8]">Model file</span>
            <input className="input mt-1 font-mono" value={m.model_path} onChange={(ev) => set(['model', 'model_path'], ev.target.value)} /></label>
        </div>

        <div className="panel p-4 space-y-3">
          <div className="panel-title">Tracker</div>
          <Sel label="Algorithm" value={t.name} options={['bytetrack', 'botsort']} onChange={(x: string) => set(['tracker', 'name'], x)} />
          <Num label="Max age (frames)" value={t.max_age} onChange={(x: number) => set(['tracker', 'max_age'], x)} />
          <Num label="Min hits to confirm" value={t.min_hits} onChange={(x: number) => set(['tracker', 'min_hits'], x)} />
          <Num label="IoU match threshold" value={t.iou_threshold} step={0.05} min={0} max={1} onChange={(x: number) => set(['tracker', 'iou_threshold'], x)} />
        </div>

        <div className="panel p-4 space-y-3">
          <div className="panel-title">Video / Processing</div>
          <Sel label="Mode" value={v.mode} options={['realtime', 'accurate', 'fast']} onChange={(x: string) => set(['video', 'mode'], x)} />
          <Num label="Frame interval (fast mode)" value={v.frame_interval} min={1} onChange={(x: number) => set(['video', 'frame_interval'], x)} />
          <Num label="Max width" value={v.max_width} step={160} onChange={(x: number) => set(['video', 'max_width'], x)} />
        </div>

        <div className="panel p-4 space-y-3">
          <div className="panel-title">Group / Convoy Analysis</div>
          <Tog label="Enabled" value={g.enabled} onChange={(x: boolean) => set(['groups', 'enabled'], x)} />
          <Num label="Distance threshold (m or px)" value={g.dmax} onChange={(x: number) => set(['groups', 'dmax'], x)} />
          <Num label="Heading threshold (°)" value={g.hmax_deg} onChange={(x: number) => set(['groups', 'hmax_deg'], x)} />
          <Num label="Persistence (s)" value={g.tmin_sec} step={0.5} onChange={(x: number) => set(['groups', 'tmin_sec'], x)} />
          <Num label="Min vehicles" value={g.min_vehicles} min={2} onChange={(x: number) => set(['groups', 'min_vehicles'], x)} />
        </div>

        <div className="panel p-4 space-y-2">
          <div className="panel-title">Event Rules</div>
          <Num label="Stopped speed (km/h)" value={e.stopped_speed_kmh} step={0.5} onChange={(x: number) => set(['events', 'stopped_speed_kmh'], x)} />
          <Num label="Stopped duration (s)" value={e.stopped_seconds} onChange={(x: number) => set(['events', 'stopped_seconds'], x)} />
          <Num label="Spacing warning (m)" value={e.spacing_warn_m} step={0.5} onChange={(x: number) => set(['events', 'spacing_warn_m'], x)} />
          {Object.keys(e.enabled || {}).map((k) => (
            <Tog key={k} label={k.replace(/_/g, ' ')} value={(e.enabled as any)[k]} onChange={(x: boolean) => set(['events', 'enabled', k], x)} />
          ))}
        </div>

        <div className="panel p-4 space-y-3">
          <div className="panel-title">UI / Overlay</div>
          <Tog label="Show trajectories" value={u.show_trajectories} onChange={(x: boolean) => set(['ui', 'show_trajectories'], x)} />
          <Num label="Trajectory history (s)" value={u.trajectory_seconds} step={1} onChange={(x: number) => set(['ui', 'trajectory_seconds'], x)} />
          <Tog label="Show labels" value={u.show_labels} onChange={(x: boolean) => set(['ui', 'show_labels'], x)} />
          <Tog label="Show confidence" value={u.show_confidence} onChange={(x: boolean) => set(['ui', 'show_confidence'], x)} />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="btn btn-primary" onClick={save}>💾 Save Settings</button>
        {msg && <span className="text-sm text-green-300">{msg}</span>}
        <span className="text-xs text-[#8fa3c8]">Applies to newly started analyses.</span>
      </div>
    </div>
  )
}
