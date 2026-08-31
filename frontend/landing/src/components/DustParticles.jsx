import { useEffect, useRef } from 'react'

/**
 * DustParticles
 * Canvas con partículas de polvo iluminado de biblioteca.
 * Movimiento browniano muy lento, sin parpadeo brusco.
 * Estética: motes de polvo flotando en luz difusa.
 */
export default function DustParticles({ opacity = 1 }) {
  const canvasRef = useRef(null)
  const animRef   = useRef(null)

  useEffect(() => {
    const canvas  = canvasRef.current
    if (!canvas) return
    const ctx     = canvas.getContext('2d')

    const resize = () => {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // ── Generar partículas ──────────────────────────────────────
    const COUNT = 55
    const particles = Array.from({ length: COUNT }, () => ({
      x:    Math.random() * canvas.width,
      y:    Math.random() * canvas.height,
      r:    Math.random() * 1.4 + 0.3,       // radio 0.3 – 1.7px
      vx:   (Math.random() - 0.5) * 0.12,    // velocidad horizontal muy baja
      vy:   -(Math.random() * 0.10 + 0.03),  // deriva lenta hacia arriba
      // Brillo base: zonas superiores más iluminadas (luz de ventana)
      brightness: Math.random() * 0.55 + 0.15,
      // Fase de parpadeo lento individual
      phase: Math.random() * Math.PI * 2,
      freq:  Math.random() * 0.003 + 0.001,
    }))

    let frame = 0
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      particles.forEach(p => {
        // Movimiento
        p.x += p.vx
        p.y += p.vy

        // Turbulencia browniana mínima
        p.vx += (Math.random() - 0.5) * 0.008
        p.vy += (Math.random() - 0.5) * 0.005

        // Amortiguar para que no acelere indefinidamente
        p.vx *= 0.995
        p.vy *= 0.995

        // Wrap en bordes
        if (p.x < -4)               p.x = canvas.width  + 4
        if (p.x > canvas.width  + 4) p.x = -4
        if (p.y < -4)               p.y = canvas.height + 4
        if (p.y > canvas.height + 4) p.y = -4

        // Opacidad pulsante muy lenta
        p.phase += p.freq
        const pulse  = 0.5 + 0.5 * Math.sin(p.phase)
        const alpha  = p.brightness * (0.6 + 0.4 * pulse)

        // Color: blanco ligeramente cálido (no verde para evitar aspecto gamer)
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)

        // Glow suave alrededor de partículas más grandes
        if (p.r > 1.0) {
          const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3.5)
          grd.addColorStop(0,   `rgba(240, 248, 240, ${alpha * 0.9})`)
          grd.addColorStop(0.5, `rgba(220, 240, 224, ${alpha * 0.3})`)
          grd.addColorStop(1,   `rgba(200, 230, 210, 0)`)
          ctx.fillStyle = grd
          ctx.arc(p.x, p.y, p.r * 3.5, 0, Math.PI * 2)
        } else {
          ctx.fillStyle = `rgba(235, 245, 238, ${alpha})`
        }

        ctx.fill()
      })

      frame++
      animRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 4, opacity }}
      aria-hidden="true"
    />
  )
}
