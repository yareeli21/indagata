import { useEffect, useRef } from 'react';

/**
 * DustParticles
 * Canvas con partículas de polvo iluminado de biblioteca.
 * Movimiento browniano muy lento, sin parpadeo brusco.
 * Estética: motes de polvo flotando en luz difusa.
 */
interface DustParticlesProps {
  opacity?: number;
}

interface Particle {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  brightness: number;
  phase: number;
  freq: number;
}

export default function DustParticles({ opacity = 1 }: DustParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // ── Generar partículas ──────────────────────────────────────
    const COUNT = 55;
    const particles: Particle[] = Array.from({ length: COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.4 + 0.3,
      vx: (Math.random() - 0.5) * 0.12,
      vy: -(Math.random() * 0.1 + 0.03),
      brightness: Math.random() * 0.55 + 0.15,
      phase: Math.random() * Math.PI * 2,
      freq: Math.random() * 0.003 + 0.001,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        // Movimiento
        p.x += p.vx;
        p.y += p.vy;

        // Turbulencia browniana mínima
        p.vx += (Math.random() - 0.5) * 0.008;
        p.vy += (Math.random() - 0.5) * 0.005;

        // Amortiguar para que no acelere indefinidamente
        p.vx *= 0.995;
        p.vy *= 0.995;

        // Wrap en bordes
        if (p.x < -4) p.x = canvas.width + 4;
        if (p.x > canvas.width + 4) p.x = -4;
        if (p.y < -4) p.y = canvas.height + 4;
        if (p.y > canvas.height + 4) p.y = -4;

        // Opacidad pulsante muy lenta
        p.phase += p.freq;
        const pulse = 0.5 + 0.5 * Math.sin(p.phase);
        const alpha = p.brightness * (0.6 + 0.4 * pulse);

        // Color: blanco ligeramente cálido
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);

        // Glow suave alrededor de partículas más grandes
        if (p.r > 1.0) {
          const grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 3.5);
          grd.addColorStop(0, `rgba(240, 248, 240, ${alpha * 0.9})`);
          grd.addColorStop(0.5, `rgba(220, 240, 224, ${alpha * 0.3})`);
          grd.addColorStop(1, `rgba(200, 230, 210, 0)`);
          ctx.fillStyle = grd;
          ctx.arc(p.x, p.y, p.r * 3.5, 0, Math.PI * 2);
        } else {
          ctx.fillStyle = `rgba(235, 245, 238, ${alpha})`;
        }

        ctx.fill();
      });

      animRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 4, opacity }}
      aria-hidden="true"
    />
  );
}
