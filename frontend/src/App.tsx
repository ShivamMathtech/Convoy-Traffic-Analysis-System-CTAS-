import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import LiveView from './pages/LiveView'
import { AnalyticsPage, MapPage, View3DPage } from './pages/MiscPages'
import EventsPage from './pages/EventsPage'
import SessionsPage from './pages/SessionsPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'
import SourceSelector from './components/SourceSelector'
import { health } from './services/api'

export default function App() {
  useEffect(() => {
    health().catch(() => console.warn('CTAS backend not reachable at /api — start it on :8000'))
  }, [])

  return (
    <>
      <SourceSelector />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="live" element={<LiveView />} />
          <Route path="map" element={<MapPage />} />
          <Route path="3d" element={<View3DPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </>
  )
}
