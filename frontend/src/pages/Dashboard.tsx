import { useStore } from '../store/useStore'
import { useSession } from '../hooks/useSessionSocket'
import SourceSelector from '../components/SourceSelector'
import VideoPanel from '../components/VideoPanel'
import VehicleSummary from '../components/VehicleSummary'
import EventFeed from '../components/EventFeed'
import ChartsPanel from '../components/ChartsPanel'
import Map2DView from '../components/Map2DView'
import View3D from '../components/View3D'

export default function Dashboard() {
  const { sessionId, setShowSourceSelector } = useStore()
  useSession(sessionId)

  if (!sessionId) {
    return (
      <>
        <SourceSelector />
        <div className="h-[70vh] flex flex-col items-center justify-center text-center">
          <div className="text-6xl mb-4">🎥</div>
          <h1 className="text-2xl font-bold mb-2">Convoy &amp; Traffic Analysis System</h1>
          <p className="text-[#8fa3c8] mb-6 max-w-md">
            AI-powered video analytics: vehicle detection, tracking, speed &amp; spacing analysis, convoy detection.
          </p>
          <button className="btn btn-primary text-lg px-8 py-3" onClick={() => setShowSourceSelector(true)}>
            ＋ SELECT SOURCE
          </button>
        </div>
      </>
    )
  }

  return (
    <>
      <SourceSelector />
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 xl:col-span-5"><VideoPanel /></div>
        <div className="col-span-12 xl:col-span-4"><Map2DView height="46vh" /></div>
        <div className="col-span-12 xl:col-span-3"><VehicleSummary /></div>
        <div className="col-span-12 xl:col-span-5"><View3D height={340} /></div>
        <div className="col-span-12 xl:col-span-4"><ChartsPanel /></div>
        <div className="col-span-12 xl:col-span-3"><EventFeed compact /></div>
      </div>
    </>
  )
}
