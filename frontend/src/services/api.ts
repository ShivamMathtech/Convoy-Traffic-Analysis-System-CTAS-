import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 60000 })

export const videosApi = {
  upload: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/videos/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000,
    })
  },
  list: () => api.get('/videos').then((r) => r.data),
}

export const streamsApi = {
  test: (url: string, kind: 'rtsp' | 'http') =>
    api.post('/streams/test', { url, kind }).then((r) => r.data),
  cameras: () => api.get('/streams/cameras').then((r) => r.data),
}

export const analysisApi = {
  start: (source_type: string, location: string, name = '', settings_override: any = {}) =>
    api.post('/analysis/start', { source_type, location, name, settings_override }).then((r) => r.data),
  pause: (id: string) => api.post(`/analysis/${id}/pause`).then((r) => r.data),
  resume: (id: string) => api.post(`/analysis/${id}/resume`).then((r) => r.data),
  stop: (id: string) => api.post(`/analysis/${id}/stop`).then((r) => r.data),
  status: (id: string) => api.get(`/analysis/${id}/status`).then((r) => r.data),
  snapshot: (id: string) => api.get(`/analysis/${id}/snapshot`).then((r) => r.data),
  setCalibration: (session_id: string, image_points: number[][], world_points: number[][], units = 'meters') =>
    api.post('/analysis/calibration', { session_id, image_points, world_points, units }).then((r) => r.data),
  setLanes: (session_id: string, lanes: any[]) =>
    api.post('/analysis/lanes', { session_id, lanes }).then((r) => r.data),
  streamUrl: (id: string) => `/api/analysis/${id}/stream`,
  wsUrl: (id: string) =>
    `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/analysis/ws/${id}`,
}

export const sessionsApi = {
  list: () => api.get('/sessions').then((r) => r.data),
  get: (id: string) => api.get(`/sessions/${id}`).then((r) => r.data),
  replay: (id: string) => api.get(`/sessions/${id}/replay`).then((r) => r.data),
  vehicles: (id: string) => api.get(`/sessions/${id}/vehicles`).then((r) => r.data),
  track: (sid: string, tid: number) => api.get(`/sessions/${sid}/tracks/${tid}`).then((r) => r.data),
  events: (id: string) => api.get(`/sessions/${id}/events`).then((r) => r.data),
  analytics: (id: string) => api.get(`/sessions/${id}/analytics`).then((r) => r.data),
  remove: (id: string) => api.delete(`/sessions/${id}`).then((r) => r.data),
}

export const reportsApi = {
  build: (id: string) => api.post(`/reports/${id}`).then((r) => r.data),
  downloadUrl: (id: string, fmt = 'pdf') => `/api/reports/${id}/download?fmt=${fmt}`,
}

export const settingsApi = {
  get: () => api.get('/settings').then((r) => r.data),
  update: (patch: any) => api.put('/settings', { patch }).then((r) => r.data),
  performance: () => api.get('/settings/performance').then((r) => r.data),
  model: () => api.get('/settings/model').then((r) => r.data),
}

export const health = () => api.get('/health').then((r) => r.data)

export default api
