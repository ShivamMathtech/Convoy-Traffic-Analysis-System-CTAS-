import { useEffect, useRef } from 'react'
import { analysisApi, sessionsApi } from '../services/api'
import { useStore } from '../store/useStore'

/** Live session hook: WebSocket for events/status + polling for vehicles/analytics. */
export function useSession(sessionId: string | null) {
  const { setStatus, pushEvent, setVehicles, setAnalytics, setEvents } = useStore()
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!sessionId) return

    let cancelled = false
    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(analysisApi.wsUrl(sessionId))
      wsRef.current = ws
      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data)
          if (data.type === 'event') pushEvent(data.event)
          else if (data.type === 'status') setStatus(data.status)
        } catch {
          /* ignore malformed frames */
        }
      }
      ws.onclose = () => {
        if (!cancelled) setTimeout(connect, 3000) // reconnect logic
      }
      ws.onerror = () => ws.close()
    }
    connect()

    const poll = async () => {
      if (cancelled) return
      try {
        const [st, veh, ana] = await Promise.all([
          analysisApi.status(sessionId).catch(() => null),
          sessionsApi.vehicles(sessionId).catch(() => null),
          sessionsApi.analytics(sessionId).catch(() => null),
        ])
        if (cancelled) return
        if (st) setStatus(st)
        if (veh) setVehicles(veh.vehicles || [])
        if (ana) setAnalytics(ana)
      } catch {
        /* transient */
      }
    }
    sessionsApi.events(sessionId).then((d) => !cancelled && setEvents(d.events || [])).catch(() => {})
    poll()
    timerRef.current = window.setInterval(poll, 1500)

    return () => {
      cancelled = true
      wsRef.current?.close()
      if (timerRef.current) window.clearInterval(timerRef.current)
    }
  }, [sessionId])
}
