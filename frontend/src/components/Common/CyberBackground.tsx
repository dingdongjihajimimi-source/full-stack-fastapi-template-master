import { useEffect, useRef } from "react"

interface Star {
  x: number
  y: number
  z: number
  color: string
}

export function CyberBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const starsRef = useRef<Star[]>([])
  const animationFrameRef = useRef<number>(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Configuration
    const STAR_COUNT = 400
    const SPEED = 2
    const COLORS = ["#ffffff", "#00f3ff", "#bd00ff"] // White, Cyan, Magenta

    // Resize handler
    const resizeCanvas = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth
        canvas.height = canvas.parentElement.clientHeight
      } else {
        canvas.width = window.innerWidth
        canvas.height = window.innerHeight
      }
    }
    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // Initialize Stars
    const initStars = () => {
      starsRef.current = []
      for (let i = 0; i < STAR_COUNT; i++) {
        starsRef.current.push({
          x: Math.random() * canvas.width - canvas.width / 2,
          y: Math.random() * canvas.height - canvas.height / 2,
          z: Math.random() * canvas.width, // Depth
          color: COLORS[Math.floor(Math.random() * COLORS.length)],
        })
      }
    }
    initStars()

    // Animation Loop
    const render = () => {
      // 1. Clear with trail effect (optional, here we do solid clear for crisp pixels)
      // Use a dark deep blue/purple background
      const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height)
      gradient.addColorStop(0, "#020010") // Deep dark blue
      gradient.addColorStop(1, "#090025") // Deep purple
      
      ctx.fillStyle = gradient
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      const cx = canvas.width / 2
      const cy = canvas.height / 2

      // 2. Update and Draw Stars
      for (const star of starsRef.current) {
        // Update depth (move towards viewer)
        star.z -= SPEED

        // Reset if passed viewer
        if (star.z <= 0) {
          star.x = Math.random() * canvas.width - cx
          star.y = Math.random() * canvas.height - cy
          star.z = canvas.width // Send back to far distance
        }

        // Project 3D to 2D
        // Perspective formula: x' = x / z * scale
        const scale = 300 // Field of view
        const sx = (star.x / star.z) * scale + cx
        const sy = (star.y / star.z) * scale + cy

        // Calculate size based on proximity
        // Closer stars = bigger pixels
        const size = Math.max(0.5, (1 - star.z / canvas.width) * 4)

        // Draw Pixel (Rectangle)
        // Only draw if within bounds
        if (sx >= 0 && sx < canvas.width && sy >= 0 && sy < canvas.height) {
          ctx.fillStyle = star.color
          // Pixel aesthetic: simple fillRect
          ctx.fillRect(sx, sy, size, size)
        }
      }

      // 3. Draw Cyber Grid (Horizon) - Optional aesthetic touch
      // Simple moving lines at the bottom
      /*
      ctx.strokeStyle = "rgba(189, 0, 255, 0.2)" // Magenta low opacity
      ctx.lineWidth = 1
      ctx.beginPath()
      // ... (Grid logic can be complex, sticking to stars for clean pixel look first)
      ctx.stroke()
      */

      animationFrameRef.current = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener("resize", resizeCanvas)
      cancelAnimationFrame(animationFrameRef.current)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full object-cover"
      style={{ imageRendering: "pixelated" }} // Ensure sharp edges
    />
  )
}
