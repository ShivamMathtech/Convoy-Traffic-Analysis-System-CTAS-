import { useState } from 'react'
import { analysisApi } from '../services/api'
import { useStore } from '../store/useStore'

export default function VideoPanel() {
  const { sessionId, status, setStatus } = useStore()
  const [speed] = useState(1)
  const [snapMsg, setSnapMsg] = useState('')

  if (!sessionId) {
    return (
      <div className="panel p-8 text-center">
        <div className="text-5xl mb-3">🎬</div>
        <div className="font-semibold mb-1">No source selected</div>
        <div className="text-sm text-[#8fa3c8] mb-4">Pick a video source to begin AI analysis.</div>
      </div>
    )
  }

  const st = status
  const paused = st?.state === 'PAUSED'

  const act = async (fn: () => Promise<any>) => {
    try { const r = await fn(); if (r.status) setStatus(r.status) } catch { /* noop */ }
  }

  const snapshot = async () => {
    try {
      const r = await analysisApi.snapshot(sessionId)
      setSnapMsg('Saved: ' + r.path)
      setTimeout(() => setSnapMsg(''), 4000)
    } catch { setSnapMsg('No frame yet') }
  }

  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e2f5c]">
        <span className="panel-title">Live Video Feed</span>
        {st && (
          <span className="text-[11px] text-[#8fa3c8] font-mono">
            Frame {st.frame}{st.total_frames ? ` / ${st.total_frames}` : ''} · {st.fps} fps src · {st.inference_fps} fps AI · {st.latency_ms} ms
          </span>
        )}
      </div>
      <div className="relative bg-black">
        <img src={analysisApi.streamUrl(sessionId)} alt="analysis stream"
          className="w-full max-h-[46vh] object-contain" draggable={false} />
        {paused && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <span className="text-2xl font-bold tracking-widest">PAUSED</span>
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-t border-[#1e2f5c]">
        {paused
          ? <button className="btn btn-primary" onClick={() => act(() => analysisApi.resume(sessionId))}>▶ Resume</button>
          : <button className="btn btn-primary" onClick={() => act(() => analysisApi.pause(sessionId))}>⏸ Pause</button>}
        <button className="btn btn-danger" onClick={() => act(() => analysisApi.stop(sessionId))}>⏹ Stop</button>
        <button className="btn btn-ghost" onClick={snapshot} title="Snapshot (S)">📷 Snapshot</button>
        <button className="btn btn-ghost" onClick={() => { const el = document.querySelector('#videopanel-full'); el?.requestFullscreen?.() }} title="Fullscreen (F)">⛶ Fullscreen</button>
        <span className="text-xs text-[#8fa3c8] ml-2">Space: play/pause · S: snapshot · F: fullscreen</span>
        {snapMsg && <span className="text-xs text-green-300 ml-auto font-mono">{snapMsg}</span>}
        {st && st.progress > 0 && (
          <div className="w-full mt-1 h-1.5 bg-[#16224a] rounded-full overflow-hidden">
            <div className="h-full bg-blue-500 transition-all" style={{ width: `${Math.min(100, st.progress)}%` }} />
          </div>
        )}
      </div>
      <span id="videopanel-full" className="hidden" />
    </div>
  )
}
