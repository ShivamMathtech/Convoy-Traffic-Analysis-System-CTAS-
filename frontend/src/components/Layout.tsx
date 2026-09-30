import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useStore } from '../store/useStore'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '▦' },
  { to: '/live', label: 'Live View', icon: '▶' },
  { to: '/map', label: '2D Map', icon: '🗺' },
  { to: '/3d', label: '3D View', icon: '🧊' },
  { to: '/analytics', label: 'Analytics', icon: '📊' },
  { to: '/events', label: 'Events', icon: '🔔' },
  { to: '/sessions', label: 'Sessions', icon: '🗂' },
  { to: '/reports', label: 'Reports', icon: '📄' },
  { to: '/settings', label: 'Settings', icon: '⚙' },
]

export default function Layout() {
  const { status, sessionId, setShowSourceSelector, reset } = useStore()
  const navigate = useNavigate()
  const state = (status?.state || 'IDLE').toUpperCase()
  const dot = state === 'RUNNING' ? 'status-live' : state === 'PAUSED' ? 'status-paused' : 'status-offline'

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-52 shrink-0 flex flex-col border-r border-[#1e2f5c] bg-[#0b1330]">
        <div className="p-4 border-b border-[#1e2f5c]">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-700 flex items-center justify-center font-black text-lg shadow-[0_0_14px_rgba(59,130,246,0.6)]">C</div>
            <div>
              <div className="font-bold text-sm leading-tight">CTAS</div>
              <div className="text-[10px] text-[#8fa3c8] leading-tight">Convoy &amp; Traffic Analysis</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-[#1a2a5c] text-white shadow-[0_0_10px_rgba(59,130,246,0.25)]' : 'text-[#8fa3c8] hover:bg-[#131f45] hover:text-white'
                }`
              }
            >
              <span className="w-5 text-center">{n.icon}</span>{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-[#1e2f5c] text-[11px] text-[#8fa3c8]">
          <div>v1.0.0 · local build</div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 shrink-0 flex items-center justify-between px-4 border-b border-[#1e2f5c] bg-[#0b1330]/80 backdrop-blur">
          <div className="flex items-center gap-3">
            <span className={`status-dot ${dot}`} />
            <span className="text-sm font-bold tracking-wider">{state}</span>
            {sessionId && <span className="text-xs text-[#8fa3c8] font-mono">{sessionId}</span>}
          </div>
          <div className="flex items-center gap-2">
            {sessionId && (
              <button className="btn btn-ghost" onClick={() => { reset(); navigate('/') }}>
                ✕ Close session
              </button>
            )}
            <button className="btn btn-primary" onClick={() => setShowSourceSelector(true)}>
              ＋ Select Source
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
