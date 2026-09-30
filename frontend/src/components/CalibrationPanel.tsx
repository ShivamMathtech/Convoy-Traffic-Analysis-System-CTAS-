import { useState } from 'react'
import { analysisApi } from '../services/api'
import { useStore } from '../store/useStore'

/** Perspective calibration + lane polygon editor for the active session. */
export default function CalibrationPanel() {
  const { sessionId } = useStore()
  const [img, setImg] = useState('0,0\n1280,0\n1280,720\n0,720')
  const [world, setWorld] = useState('0,0\n20,0\n20,8\n0,8')
  const [lanes, setLanes] = useState('[\n  {"id":"1","name":"Lane 1","polygon":[[0,0],[640,0],[640,720],[0,720]]},\n  {"id":"2","name":"Lane 2","polygon":[[640,0],[1280,0],[1280,720],[640,720]]}\n]')
  const [msg, setMsg] = useState('')

  if (!sessionId) return null

  const parse = (s: string) => s.split('\n').map((l) => l.split(',').map((x) => parseFloat(x.trim())))

  const applyCal = async () => {
    try {
      const r = await analysisApi.setCalibration(sessionId, parse(img), parse(world), 'meters')
      setMsg(r.is_calibrated ? '✓ Calibrated — metric units enabled' : 'Calibration response unexpected')
    } catch (e: any) {
      setMsg('Error: ' + (e?.response?.data?.detail || e.message))
    }
    setTimeout(() => setMsg(''), 5000)
  }

  const applyLanes = async () => {
    try {
      await analysisApi.setLanes(sessionId, JSON.parse(lanes))
      setMsg('✓ Lanes updated')
    } catch (e: any) {
      setMsg('Error: ' + (e?.response?.data?.detail || e.message))
    }
    setTimeout(() => setMsg(''), 5000)
  }

  return (
    <div className="panel p-4 space-y-4">
      <div>
        <div className="panel-title mb-2">Perspective Calibration</div>
        <p className="text-xs text-[#8fa3c8] mb-2">
          Pick 4 image reference points (u,v) and their known ground coordinates (X,Y in meters).
          Metric speed/distance appear only after calibration — otherwise pixel units are shown.
        </p>
        <div className="grid grid-cols-2 gap-2">
          <label className="block"><span className="text-xs text-[#8fa3c8]">Image points (u,v ×4)</span>
            <textarea className="input font-mono mt-1" rows={4} value={img} onChange={(e) => setImg(e.target.value)} /></label>
          <label className="block"><span className="text-xs text-[#8fa3c8]">World points (X,Y ×4, meters)</span>
            <textarea className="input font-mono mt-1" rows={4} value={world} onChange={(e) => setWorld(e.target.value)} /></label>
        </div>
        <button className="btn btn-primary mt-2" onClick={applyCal}>Apply Calibration</button>
      </div>
      <div>
        <div className="panel-title mb-2">Lane Polygons</div>
        <textarea className="input font-mono" rows={6} value={lanes} onChange={(e) => setLanes(e.target.value)} />
        <button className="btn btn-primary mt-2" onClick={applyLanes}>Apply Lanes</button>
      </div>
      {msg && <div className="text-sm text-green-300">{msg}</div>}
    </div>
  )
}
