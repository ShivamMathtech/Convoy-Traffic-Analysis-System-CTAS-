import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useStore } from '../store/useStore'

const COLORS: Record<string, number> = {
  car: 0x38bdf8, truck: 0x6366f1, bus: 0xf59e0b, van: 0x34d399,
  motorcycle: 0xe879f9, bicycle: 0x4ade80, other: 0x94a3b8,
}

function labelSprite(text: string): THREE.Sprite {
  const c = document.createElement('canvas')
  c.width = 128; c.height = 48
  const g = c.getContext('2d')!
  g.fillStyle = 'rgba(10,17,40,0.85)'
  g.fillRect(0, 0, 128, 48)
  g.fillStyle = '#e6ecf5'
  g.font = 'bold 26px sans-serif'
  g.textAlign = 'center'
  g.fillText(text, 64, 33)
  const tex = new THREE.CanvasTexture(c)
  const mat = new THREE.SpriteMaterial({ map: tex, depthTest: false })
  const sp = new THREE.Sprite(mat)
  sp.scale.set(6, 2.25, 1)
  return sp
}

/** 3D Localization — perspective view. X/Y from image plane (world coords when
 *  calibrated); Z stays 0 — depth is never fabricated. */
export default function View3D({ height = 420 }: { height?: number }) {
  const mountRef = useRef<HTMLDivElement>(null)
  const { vehicles } = useStore()
  const sceneRef = useRef<{ scene: THREE.Scene; group: THREE.Group } | null>(null)

  useEffect(() => {
    const el = mountRef.current
    if (!el) return
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a1128)
    const camera = new THREE.PerspectiveCamera(55, el.clientWidth / height, 0.1, 2000)
    camera.position.set(0, -38, 30)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(el.clientWidth, height)
    el.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 0, 0)

    const grid = new THREE.GridHelper(120, 24, 0x2a3f73, 0x16224a)
    grid.rotation.x = Math.PI / 2
    scene.add(grid)
    const axes = new THREE.AxesHelper(14)
    scene.add(axes)
    // road plane
    const road = new THREE.Mesh(
      new THREE.PlaneGeometry(100, 30),
      new THREE.MeshBasicMaterial({ color: 0x141d38, side: THREE.DoubleSide }),
    )
    scene.add(road)
    for (const y of [-5, 5]) {
      const line = new THREE.Mesh(
        new THREE.PlaneGeometry(100, 0.3),
        new THREE.MeshBasicMaterial({ color: 0x5b6b8c }),
      )
      line.position.y = y
      line.position.z = 0.05
      scene.add(line)
    }
    scene.add(new THREE.AmbientLight(0xffffff, 0.9))
    const dir = new THREE.DirectionalLight(0xffffff, 0.8)
    dir.position.set(20, -20, 40)
    scene.add(dir)

    const group = new THREE.Group()
    scene.add(group)
    sceneRef.current = { scene, group }

    let raf = 0
    const animate = () => { raf = requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera) }
    animate()
    const onResize = () => {
      camera.aspect = el.clientWidth / height
      camera.updateProjectionMatrix()
      renderer.setSize(el.clientWidth, height)
    }
    window.addEventListener('resize', onResize)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', onResize); renderer.dispose(); el.removeChild(renderer.domElement); sceneRef.current = null }
  }, [])

  useEffect(() => {
    const ref = sceneRef.current
    if (!ref) return
    const { group } = ref
    while (group.children.length) {
      const c = group.children.pop()!
      group.remove(c)
    }
    let mw = 1280, mh = 720
    vehicles.forEach((v) => { mw = Math.max(mw, v.bbox[2]); mh = Math.max(mh, v.bbox[3]) })
    vehicles.forEach((v) => {
      const x = (v.centroid[0] / mw - 0.5) * 100
      const y = -(v.centroid[1] / mh - 0.5) * 60
      const color = COLORS[v.class_name] ?? COLORS.other
      const big = v.class_name === 'truck' || v.class_name === 'bus'
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(big ? 7 : 4.4, big ? 3 : 2.2, big ? 3.4 : 1.8),
        new THREE.MeshLambertMaterial({ color }),
      )
      mesh.position.set(x, y, 1.2)
      const label = labelSprite(`ID ${v.track_id}`)
      label.position.set(x, y, 5)
      group.add(mesh)
      group.add(label)
    })
  }, [vehicles])

  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="panel-title">3D Localization — Perspective View</span>
        <span className="text-[11px] text-[#8fa3c8]">drag: rotate · wheel: zoom · right-drag: pan</span>
      </div>
      <div ref={mountRef} style={{ height }} className="rounded-lg overflow-hidden border border-[#1e2f5c]" />
      <div className="text-[11px] text-[#8fa3c8] mt-2">Z = 0 for all vehicles — monocular video has no true depth; it is not fabricated.</div>
    </div>
  )
}
