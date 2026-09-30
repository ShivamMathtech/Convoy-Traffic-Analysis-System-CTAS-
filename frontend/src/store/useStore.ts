import { create } from 'zustand'
import type { AnalyticsPayload, CtasEvent, SessionStatus, Vehicle } from '../types'

interface CtasState {
  sessionId: string | null
  status: SessionStatus | null
  vehicles: Vehicle[]
  events: CtasEvent[]
  analytics: AnalyticsPayload | null
  unit: string
  showSourceSelector: boolean
  setSession: (id: string | null) => void
  setStatus: (s: SessionStatus | null) => void
  setVehicles: (v: Vehicle[]) => void
  pushEvent: (e: CtasEvent) => void
  setEvents: (e: CtasEvent[]) => void
  setAnalytics: (a: AnalyticsPayload | null) => void
  setShowSourceSelector: (b: boolean) => void
  reset: () => void
}

export const useStore = create<CtasState>((set) => ({
  sessionId: null,
  status: null,
  vehicles: [],
  events: [],
  analytics: null,
  unit: 'px',
  showSourceSelector: false,
  setSession: (sessionId) => set({ sessionId, vehicles: [], events: [], analytics: null, status: null }),
  setStatus: (status) => set({ status }),
  setVehicles: (vehicles) => set({ vehicles }),
  pushEvent: (e) => set((s) => ({ events: [...s.events.slice(-499), e] })),
  setEvents: (events) => set({ events }),
  setAnalytics: (analytics) => set({ analytics }),
  setShowSourceSelector: (showSourceSelector) => set({ showSourceSelector }),
  reset: () => set({ sessionId: null, status: null, vehicles: [], events: [], analytics: null }),
}))
