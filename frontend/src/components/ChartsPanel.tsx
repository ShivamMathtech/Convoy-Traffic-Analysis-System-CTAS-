import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import { useStore } from '../store/useStore'

function useChart(ref: React.RefObject<HTMLDivElement>, option: any) {
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' })
    chart.setOption(option)
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => { window.removeEventListener('resize', onResize); chart.dispose() }
  }, [JSON.stringify(option)])
}

const AXIS = {
  axisLine: { lineStyle: { color: '#2a3f73' } },
  axisLabel: { color: '#8fa3c8', fontSize: 10 },
  splitLine: { lineStyle: { color: '#16224a' } },
}

export function CountChart() {
  const ref = useRef<HTMLDivElement>(null)
  const { analytics } = useStore()
  const a = analytics
  const series = a ? Object.entries(a.class_counts_over_time).map(([cls, pts]) => ({
    name: cls, type: 'line' as const, stack: 'total', smooth: true, showSymbol: false,
    data: pts.map((p) => [p.t, p.v]),
  })) : []
  useChart(ref, {
    title: { text: 'Vehicle Count Over Time', textStyle: { color: '#c7d4ee', fontSize: 12 } },
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#8fa3c8', fontSize: 10 }, top: 24 },
    grid: { left: 36, right: 12, top: 52, bottom: 24 },
    xAxis: { type: 'time', ...AXIS },
    yAxis: { type: 'value', ...AXIS },
    series: series.length ? series : [{ type: 'line', data: [] }],
  })
  return <div ref={ref} className="w-full h-56" />
}

export function SpeedChart() {
  const ref = useRef<HTMLDivElement>(null)
  const { vehicles, analytics } = useStore()
  const speeds = vehicles.map((v) => v.speed).filter((s): s is number => s != null)
  const bins = new Array(12).fill(0)
  const max = Math.max(60, ...speeds)
  speeds.forEach((s) => { bins[Math.min(11, Math.floor((s / max) * 12))]++ })
  const unit = analytics?.unit || 'px/s'
  useChart(ref, {
    title: { text: `Speed Distribution (${unit})`, textStyle: { color: '#c7d4ee', fontSize: 12 } },
    grid: { left: 36, right: 12, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: bins.map((_, i) => `${Math.round((i / 12) * max)}`), ...AXIS },
    yAxis: { type: 'value', ...AXIS },
    series: [{ type: 'bar', data: bins, itemStyle: { color: '#3b82f6', borderRadius: [3, 3, 0, 0] } }],
  })
  return <div ref={ref} className="w-full h-56" />
}

export function SpacingChart() {
  const ref = useRef<HTMLDivElement>(null)
  const { analytics } = useStore()
  const pts = analytics?.spacing_over_time || []
  const unit = analytics?.unit || 'px'
  useChart(ref, {
    title: { text: `Inter-Vehicle Spacing (${unit})`, textStyle: { color: '#c7d4ee', fontSize: 12 } },
    grid: { left: 44, right: 12, top: 36, bottom: 24 },
    xAxis: { type: 'time', ...AXIS },
    yAxis: { type: 'value', ...AXIS },
    series: [{ type: 'line', smooth: true, showSymbol: false, data: pts.map((p) => [p.t, p.v]), itemStyle: { color: '#22c55e' } }],
  })
  return <div ref={ref} className="w-full h-56" />
}

export function ClassDonut() {
  const ref = useRef<HTMLDivElement>(null)
  const { vehicles } = useStore()
  const counts: Record<string, number> = {}
  vehicles.forEach((v) => { counts[v.class_name] = (counts[v.class_name] || 0) + 1 })
  useChart(ref, {
    title: { text: 'Class Distribution', textStyle: { color: '#c7d4ee', fontSize: 12 } },
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      label: { color: '#c7d4ee', fontSize: 10 },
      data: Object.entries(counts).map(([name, value]) => ({ name, value })),
    }],
  })
  return <div ref={ref} className="w-full h-56" />
}

export default function ChartsPanel() {
  return (
    <div className="panel p-4">
      <div className="panel-title mb-3">Analytics</div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <CountChart />
        <SpeedChart />
        <SpacingChart />
        <ClassDonut />
      </div>
    </div>
  )
}
