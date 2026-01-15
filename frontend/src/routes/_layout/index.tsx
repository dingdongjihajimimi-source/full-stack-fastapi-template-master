import { createFileRoute } from "@tanstack/react-router"
import { useEffect, useRef } from "react"

import { CyberBackground } from "@/components/Common/CyberBackground"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "全/半自动化脚本工具",
      },
    ],
  }),
})

// Particle Class
class Particle {
  x: number
  y: number
  vx: number
  vy: number
  alpha: number
  color: string
  decay: number

  constructor(x: number, y: number, color: string) {
    this.x = x
    this.y = y
    this.color = color
    this.alpha = 1.0

    // Explosion physics
    const angle = Math.random() * Math.PI * 2
    // Random speed between 2 and 6
    const speed = Math.random() * 4 + 2

    this.vx = Math.cos(angle) * speed
    this.vy = Math.sin(angle) * speed

    // Decay rate (lifespan)
    this.decay = Math.random() * 0.015 + 0.005
  }

  update() {
    // Gravity
    this.vy += 0.05
    // Friction
    this.vx *= 0.98
    this.vy *= 0.98

    this.x += this.vx
    this.y += this.vy
    this.alpha -= this.decay
  }

  draw(ctx: CanvasRenderingContext2D) {
    ctx.globalAlpha = this.alpha
    ctx.fillStyle = this.color
    ctx.beginPath()
    ctx.arc(this.x, this.y, 2, 0, Math.PI * 2)
    ctx.fill()
  }
}

function Dashboard() {
  const { user: currentUser } = useAuth()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const animationFrameRef = useRef<number>(0)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // 1. Canvas Sizing
    const resizeCanvas = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth
        canvas.height = canvas.parentElement.clientHeight
      }
    }
    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // 2. WebSocket Connection
    const connectWebSocket = () => {
      // Adjust this if your API is on a different port in dev
      const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000"
      const wsUrl = `${apiBase.replace(/^http/, "ws")}/api/v1/fireworks/stream`

      const ws = new WebSocket(wsUrl)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // data: { x: 0-100, y: 0-100, color: hex, type: string, intensity: 0.0-1.0 }

          const screenX = (data.x / 100) * canvas.width
          const screenY = (data.y / 100) * canvas.height

          // Instantiate 50-100 particles
          const particleCount = Math.floor(Math.random() * 50) + 50
          for (let i = 0; i < particleCount; i++) {
            particlesRef.current.push(
              new Particle(screenX, screenY, data.color)
            )
          }
        } catch (e) {
          console.error("Error parsing firework data", e)
        }
      }

      ws.onclose = () => {
        // Optional: Reconnect logic could go here
      }

      wsRef.current = ws
    }

    connectWebSocket()

    // 3. Animation Loop
    const render = () => {
      // Clear canvas with a slight trail effect (optional, here we clear fully)
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      // Or use this for trails:
      // ctx.globalAlpha = 0.1; ctx.fillStyle = 'black'; ctx.fillRect(0,0,w,h);

      // Update and draw particles
      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i]
        p.update()
        p.draw(ctx)

        // Remove dead particles
        if (p.alpha <= 0) {
          particlesRef.current.splice(i, 1)
        }
      }

      animationFrameRef.current = requestAnimationFrame(render)
    }

    render()

    // Cleanup
    return () => {
      window.removeEventListener("resize", resizeCanvas)
      cancelAnimationFrame(animationFrameRef.current)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  return (
    <div className="relative h-[calc(100vh-14rem)] overflow-hidden rounded-2xl shadow-2xl border border-white/10">
      {/* Layer 3: Fireworks Canvas - Now relative to this container */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 pointer-events-none z-50"
      />

      {/* Layer 1: Background Video + Overlay */}
      <div className="absolute inset-0 z-0">
        <CyberBackground />
        <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" />
      </div>

      {/* Layer 2: Content */}
      <div className="relative z-10 p-12 h-full flex flex-col justify-center items-start">
        <h1 className="text-5xl font-extrabold tracking-tighter mb-4 text-white drop-shadow-2xl">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-2xl text-white/70 font-light">
          Welcome back! The universe is waiting for your next command.
        </p>
      </div>
    </div>
  )
}
