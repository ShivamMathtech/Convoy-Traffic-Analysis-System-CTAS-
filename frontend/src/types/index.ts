export interface Vehicle {
  track_id: number
  class_name: string
  confidence: number
  bbox: number[]
  centroid: number[]
  speed: number | null
  speed_unit?: string
  heading: number | null
  lane: string | null
  group_id: number | null
}

export interface CtasEvent {
  timestamp: number
  event_type: string
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH'
  track_id: number | null
  description: string
}

export interface SessionStatus {
  session_id: string
  state: string
  frame: number
  total_frames: number
  fps: number
  inference_fps: number
  latency_ms: number
  progress: number
  source: string
  model_loaded: boolean
  error?: string | null
}

export interface AnalyticsPayload {
  vehicle_count_over_time: { t: number; v: number | null }[]
  average_speed_over_time: { t: number; v: number | null }[]
  spacing_over_time: { t: number; v: number | null }[]
  group_count_over_time: { t: number; v: number | null }[]
  class_counts_over_time: Record<string, { t: number; v: number }[]>
  total_entered: number
  calibrated?: boolean
  unit?: string
}

export interface SessionMeta {
  id: string
  name: string
  source_type: string
  source_path: string
  started_at: string | null
  status: string
  fps: number
  width: number
  height: number
  total_frames: number
  vehicles?: number
  events?: number
}
