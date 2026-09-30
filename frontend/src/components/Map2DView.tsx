import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { useStore } from '../store/useStore'

const COLORS: Record<string, string> = {
  car: '#38bdf8', truck: '#6366f1', bus: '#f59e0b', van: '#34d399',
  motorcycle: '#e879f9', bicycle: '#4ade80', other: '#94a3b8',
}

/** 2D Localization — top view. Uses normalized image coords; when the session
 *  is calibrated the backend already supplies world coords via analytics. */
export default function Map2DView({ height = '100%' }: { height?: string }) {
  const mapRef = useRef<HTMLDivElement>(null)
  const mapObj = useRef<L.Map | null>(null)
  const layer = useRef<L.LayerGroup | null>(null)
  const { vehicles, status } = useStore()

  useEffect(() => {
    if (!mapRef.current || mapObj.current) return
    const map = L.map(mapRef.current, { crs: L.CRS.Simple, zoomControl: true, attributionControl: false })
    const W = 1000, H = 600
    const bounds = [[0, 0], [H, W]] as L.LatLngBoundsExpression
    L.rectangle(bounds, { color: '#2a3f73', weight: 1, fillColor: '#0d1530', fillOpacity: 1 }).addTo(map)
    // road band
    L.rectangle([[H * 0.25, 0], [H * 0.75, W]], { color: '#3b537f', weight: 1, fillColor: '#1a2440', fillOpacity: 1 }).addTo(map)
    // lane dividers
    for (const f of [0.42, 0.58]) {
      L.polyline([[H * f, 0], [H * f, W]], { color: '#5b6b8c', weight: 1, dashArray: '8 8' }).addTo(map)
    }
    map.fitBounds(bounds)
    mapObj.current = map
    layer.current = L.layerGroup().addTo(map)
    return () => { map.remove(); mapObj.current = null }
  }, [])

  useEffect(() => {
    const lg = layer.current
    if (!lg) return
    lg.clearLayers()
    const W = 1000, H = 600
    // normalize by max bbox extent seen (fallback 1280x720)
    let mw = 1280, mh = 720
    vehicles.forEach((v) => {
      mw = Math.max(mw, v.bbox[2]); mh = Math.max(mh, v.bbox[3])
    })
    vehicles.forEach((v) => {
      const x = (v.centroid[0] / mw) * W
      const y = (v.centroid[1] / mh) * H
      const color = COLORS[v.class_name] || COLORS.other
      const m = L.circleMarker([y, x], { radius: 7, color, fillColor: color, fillOpacity: 0.85, weight: 2 })
      m.bindTooltip(`ID ${v.track_id} · ${v.class_name}${v.speed != null ? ` · ${v.speed.toFixed(1)} ${v.speed_unit || ''}` : ''}${v.lane ? ` · ${v.lane}` : ''}`)
      // heading arrow
      if (v.heading != null) {
        const a = (v.heading * Math.PI) / 180
        const x2 = x + Math.cos(a) * 26, y2 = y + Math.sin(a) * 26
        L.polyline([[y, x], [y2, x2]], { color, weight: 2 }).addTo(lg)
      }
      m.addTo(lg)
    })
  }, [vehicles])

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <span className="panel-title">2D Localization — Top View</span>
        <span className="text-[11px] text-[#8fa3c8]">
          {status ? `${vehicles.length} vehicles` : 'no session'} · click a marker for details
        </span>
      </div>
      <div ref={mapRef} style={{ height, minHeight: 320 }} className="rounded-lg overflow-hidden border border-[#1e2f5c] z-0" />
      <div className="flex flex-wrap gap-3 mt-2 text-[11px] text-[#8fa3c8]">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1 capitalize">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: c }} />{k}
          </span>
        ))}
      </div>
    </div>
  )
}
