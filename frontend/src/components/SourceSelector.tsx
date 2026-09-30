import { useEffect, useRef, useState } from 'react'
import { analysisApi, streamsApi, videosApi } from '../services/api'
import { useStore } from '../store/useStore'

type Tab = 'upload' | 'video' | 'image' | 'camera' | 'rtsp' | 'http' | 'demo'

export default function SourceSelector() {
  const { showSourceSelector, setShowSourceSelector, setSession } = useStore()
  const [tab, setTab] = useState<Tab>('upload')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [uploadMeta, setUploadMeta] = useState<any>(null)
  const [videos, setVideos] = useState<any[]>([])
  const [cameras, setCameras] = useState<any[]>([])
  const [rtsp, setRtsp] = useState('')
  const [http, setHttp] = useState('')
  const [camIdx, setCamIdx] = useState('0')
  const [imgDir, setImgDir] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!showSourceSelector) return
    setError('')
    videosApi.list().then((d) => setVideos(d.videos || [])).catch(() => {})
    streamsApi.cameras().then((d) => setCameras(d.cameras || [])).catch(() => {})
  }, [showSourceSelector])

  if (!showSourceSelector) return null

  const start = async (source_type: string, location: string, name = '') => {
    setBusy(true)
    setError('')
    try {
      const r = await analysisApi.start(source_type, location, name || `${source_type}-${Date.now()}`)
      setSession(r.session_id)
      setShowSourceSelector(false)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to start analysis')
    } finally {
      setBusy(false)
    }
  }

  const onFile = async (f: File) => {
    setBusy(true)
    setError('')
    try {
      const r = await videosApi.upload(f)
      setUploadMeta(r.data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  const testRtsp = async () => {
    setBusy(true); setError('')
    try {
      await streamsApi.test(rtsp, 'rtsp')
      await start('rtsp', rtsp, 'rtsp-stream')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'RTSP unreachable')
    } finally { setBusy(false) }
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'upload', label: 'Upload Video' },
    { id: 'video', label: 'Existing Video' },
    { id: 'image', label: 'Image' },
    { id: 'camera', label: 'Local Camera' },
    { id: 'rtsp', label: 'RTSP' },
    { id: 'http', label: 'HTTP' },
    { id: 'demo', label: 'Demo' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => !busy && setShowSourceSelector(false)}>
      <div className="panel w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold tracking-wide">SELECT VIDEO SOURCE</h2>
          <button className="btn btn-ghost" onClick={() => setShowSourceSelector(false)}>✕</button>
        </div>
        <div className="flex flex-wrap gap-2 mb-5">
          {tabs.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`btn ${tab === t.id ? 'btn-primary' : 'btn-ghost'}`}>{t.label}</button>
          ))}
        </div>

        {error && <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800 text-sm text-red-200">{error}</div>}

        {tab === 'upload' && (
          <div>
            <div
              className="border-2 border-dashed border-[#2a3f73] rounded-xl p-10 text-center cursor-pointer hover:border-blue-500 transition-colors"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onFile(f) }}
            >
              <div className="text-4xl mb-2">📤</div>
              <div className="font-semibold">Drag &amp; drop a video here, or click to browse</div>
              <div className="text-xs text-[#8fa3c8] mt-1">MP4 · AVI · MOV · MKV · WEBM (max 1 GB)</div>
              <input ref={fileRef} type="file" className="hidden" accept="video/*"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f) }} />
            </div>
            {uploadMeta && (
              <div className="mt-4 p-4 rounded-lg bg-[#0d1530] border border-[#24365e] text-sm">
                <div className="font-semibold mb-1">{uploadMeta.filename}</div>
                <div className="text-[#8fa3c8] text-xs">
                  {uploadMeta.width}×{uploadMeta.height} · {uploadMeta.fps} fps · {uploadMeta.frames} frames
                  {uploadMeta.duration_s ? ` · ${uploadMeta.duration_s}s` : ''} · {(uploadMeta.size_bytes / 1e6).toFixed(1)} MB
                </div>
                <button className="btn btn-primary mt-3" disabled={busy}
                  onClick={() => start('video', uploadMeta.stored_as, uploadMeta.filename)}>
                  ▶ START ANALYSIS
                </button>
              </div>
            )}
          </div>
        )}

        {tab === 'video' && (
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {videos.length === 0 && <div className="text-sm text-[#8fa3c8]">No uploaded videos yet.</div>}
            {videos.map((v) => (
              <div key={v.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0d1530] border border-[#24365e] text-sm">
                <div>
                  <div className="font-semibold">{v.filename}</div>
                  <div className="text-xs text-[#8fa3c8]">{v.width}×{v.height} · {v.frames} frames</div>
                </div>
                <button className="btn btn-primary" disabled={busy} onClick={() => start('video', v.id, v.filename)}>Analyze</button>
              </div>
            ))}
          </div>
        )}

        {tab === 'image' && (
          <div className="space-y-3">
            <p className="text-sm text-[#8fa3c8]">Analyze a single image or a directory of images (JPG/PNG/WEBP).</p>
            <input className="input" placeholder="Image directory path on the server, e.g. /data/frames"
              value={imgDir} onChange={(e) => setImgDir(e.target.value)} />
            <button className="btn btn-primary" disabled={busy || !imgDir} onClick={() => start('image_dir', imgDir, 'image-dir')}>▶ START ANALYSIS</button>
          </div>
        )}

        {tab === 'camera' && (
          <div className="space-y-3">
            <p className="text-sm text-[#8fa3c8]">Local webcam / USB camera by device index.</p>
            {cameras.length > 0 ? (
              <div className="space-y-2">
                {cameras.map((c: any) => (
                  <div key={c.index} className="flex items-center justify-between p-3 rounded-lg bg-[#0d1530] border border-[#24365e] text-sm">
                    <span>{c.label}</span>
                    <button className="btn btn-primary" disabled={busy} onClick={() => start('webcam', String(c.index), `camera-${c.index}`)}>Use</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex gap-2">
                <input className="input" value={camIdx} onChange={(e) => setCamIdx(e.target.value)} placeholder="Camera index (0, 1, 2…)" />
                <button className="btn btn-primary" disabled={busy} onClick={() => start('webcam', camIdx, `camera-${camIdx}`)}>▶ START</button>
              </div>
            )}
          </div>
        )}

        {tab === 'rtsp' && (
          <div className="space-y-3">
            <input className="input font-mono" placeholder="rtsp://user:password@host:port/path"
              value={rtsp} onChange={(e) => setRtsp(e.target.value)} />
            <button className="btn btn-primary" disabled={busy || !rtsp} onClick={testRtsp}>Test &amp; Start</button>
            <p className="text-xs text-[#8fa3c8]">Password is masked in logs; the connection is tested before analysis starts.</p>
          </div>
        )}

        {tab === 'http' && (
          <div className="space-y-3">
            <input className="input font-mono" placeholder="http(s)://host/stream (MJPEG)"
              value={http} onChange={(e) => setHttp(e.target.value)} />
            <button className="btn btn-primary" disabled={busy || !http} onClick={() => start('http', http, 'http-stream')}>▶ START ANALYSIS</button>
          </div>
        )}

        {tab === 'demo' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-amber-950/50 border border-amber-800 text-sm text-amber-200">
              DEMO / SYNTHETIC DATA — computer-generated traffic scene. Used to exercise the full
              pipeline without a camera or AI model. Never confused with real detections.
            </div>
            <button className="btn btn-primary" disabled={busy} onClick={() => start('demo', 'synthetic', 'demo')}>▶ START DEMO</button>
          </div>
        )}

        {busy && <div className="mt-4 text-sm text-[#8fa3c8]">Working…</div>}
      </div>
    </div>
  )
}
