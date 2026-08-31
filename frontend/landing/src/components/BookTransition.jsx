import { motion, useAnimation } from 'framer-motion'
import { useEffect } from 'react'

/**
 * BookTransition
 *
 * Un libro ilustrado que aparece en el centro de la pantalla.
 * Secuencia:
 *   1. El libro (cerrado) entra desde abajo con un fade-up
 *   2. Páginas interiores pasan rápido simulando el paso de hojas
 *   3. La tapa delantera se abre (rotación 3D sobre eje Y izquierdo)
 *   4. El libro completo hace fade-out y escala hacia arriba
 *   5. onDone() se llama — la frase puede aparecer
 *
 * Props:
 *   onDone  — callback cuando termina
 */
export default function BookTransition({ onDone }) {
  const coverControls = useAnimation()
  const bookControls  = useAnimation()
  const page1Controls = useAnimation()
  const page2Controls = useAnimation()
  const page3Controls = useAnimation()

  useEffect(() => {
    const run = async () => {

      // ── 1. Libro cerrado entra desde abajo ────────────────────
      await bookControls.start({
        y:       0,
        opacity: 1,
        transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] },
      })

      // ── 2. Pausa breve — el libro respira ────────────────────
      await new Promise(r => setTimeout(r, 320))

      // ── 3. Páginas pasan una por una (paso de hojas) ─────────
      // Página 1
      await page1Controls.start({
        rotateY: -180,
        transition: { duration: 0.42, ease: [0.4, 0, 0.6, 1] },
      })
      await new Promise(r => setTimeout(r, 60))

      // Página 2
      await page2Controls.start({
        rotateY: -180,
        transition: { duration: 0.38, ease: [0.4, 0, 0.6, 1] },
      })
      await new Promise(r => setTimeout(r, 55))

      // Página 3
      await page3Controls.start({
        rotateY: -180,
        transition: { duration: 0.35, ease: [0.4, 0, 0.6, 1] },
      })

      // ── 4. Pausa antes de abrir tapa ──────────────────────────
      await new Promise(r => setTimeout(r, 200))

      // ── 5. Tapa delantera se abre ─────────────────────────────
      await coverControls.start({
        rotateY: -175,
        transition: { duration: 0.9, ease: [0.16, 1, 0.3, 1] },
      })

      // ── 6. Pausa — libro abierto visible un instante ──────────
      await new Promise(r => setTimeout(r, 350))

      // ── 7. Libro sube y desaparece ────────────────────────────
      await bookControls.start({
        y:       -60,
        opacity: 0,
        scale:   1.06,
        transition: { duration: 0.65, ease: [0.4, 0, 1, 1] },
      })

      onDone()
    }

    run()
  }, [])

  // ── Dimensiones del libro (relativas al viewport) ─────────────
  const W = 'clamp(200px, 22vw, 320px)'
  const H = 'clamp(260px, 28vw, 400px)'

  // Colores de páginas interiores — papeles envejecidos
  const PAGE_COLORS = ['#0E1A10', '#0C1A0E', '#101C12']

  // ── Líneas de texto simuladas en las páginas ──────────────────
  const TextLines = ({ color = 'rgba(168,213,162,0.12)', count = 8 }) => (
    <div className="absolute inset-0 flex flex-col justify-center px-4 gap-2 pt-6">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            height:          '1.5px',
            borderRadius:    '1px',
            background:      color,
            width:           i % 3 === 2 ? '65%' : i % 2 === 0 ? '92%' : '78%',
            opacity:         0.6 + (i % 3) * 0.1,
          }}
        />
      ))}
    </div>
  )

  return (
    <motion.div
      className="fixed inset-0 z-40 pointer-events-none flex items-center justify-center"
      style={{ perspective: '1200px' }}
    >
      {/* Halo de luz suave detrás del libro */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width:      'clamp(300px, 35vw, 500px)',
          height:     'clamp(300px, 35vw, 500px)',
          background: 'radial-gradient(ellipse, rgba(74,222,128,0.06) 0%, rgba(6,10,7,0) 70%)',
          filter:     'blur(24px)',
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
      />

      {/* ── El libro ──────────────────────────────────────────────── */}
      <motion.div
        animate={bookControls}
        initial={{ y: 80, opacity: 0, scale: 1 }}
        style={{
          width:           W,
          height:          H,
          position:        'relative',
          transformStyle:  'preserve-3d',
        }}
      >
        {/* ── Contraportada (fondo del libro) ─────────────────── */}
        <div
          style={{
            position:     'absolute',
            inset:        0,
            borderRadius: '3px 8px 8px 3px',
            background:   'linear-gradient(135deg, #0A1A0C 0%, #0D2010 100%)',
            border:       '1px solid rgba(168,213,162,0.08)',
            boxShadow:    '4px 6px 32px rgba(0,0,0,0.7), inset -2px 0 8px rgba(0,0,0,0.4)',
          }}
        />

        {/* ── Lomo del libro ──────────────────────────────────── */}
        <div
          style={{
            position:        'absolute',
            left:            '-10px',
            top:             0,
            bottom:          0,
            width:           '10px',
            borderRadius:    '3px 0 0 3px',
            background:      'linear-gradient(to right, #061008, #0A1A0C)',
            border:          '1px solid rgba(168,213,162,0.06)',
            borderRight:     'none',
            display:         'flex',
            alignItems:      'center',
            justifyContent:  'center',
          }}
        >
          {/* Título vertical en el lomo */}
          <span
            style={{
              fontFamily:    '"Space Grotesk", sans-serif',
              fontWeight:    700,
              fontSize:      '6px',
              letterSpacing: '0.22em',
              color:         'rgba(168,213,162,0.35)',
              writingMode:   'vertical-rl',
              textTransform: 'uppercase',
              userSelect:    'none',
            }}
          >
            INDAGATA
          </span>
        </div>

        {/* ── Páginas interiores (3 capas) ─────────────────────── */}
        {[page1Controls, page2Controls, page3Controls].map((ctrl, i) => (
          <motion.div
            key={i}
            animate={ctrl}
            initial={{ rotateY: 0 }}
            style={{
              position:        'absolute',
              inset:           `${i * 2}px`,
              borderRadius:    '2px 6px 6px 2px',
              background:      PAGE_COLORS[i],
              transformOrigin: 'left center',
              transformStyle:  'preserve-3d',
              backfaceVisibility: 'hidden',
              boxShadow:       'inset -3px 0 10px rgba(0,0,0,0.3)',
              overflow:        'hidden',
              border:          '1px solid rgba(168,213,162,0.05)',
            }}
          >
            <TextLines
              color="rgba(168,213,162,0.10)"
              count={7 - i}
            />
            {/* Número de página simulado */}
            <div
              style={{
                position:    'absolute',
                bottom:      '10px',
                right:       '14px',
                fontFamily:  '"DM Mono", monospace',
                fontSize:    '7px',
                color:       'rgba(168,213,162,0.2)',
                userSelect:  'none',
              }}
            >
              {(i + 1) * 24}
            </div>
          </motion.div>
        ))}

        {/* ── Tapa delantera ──────────────────────────────────── */}
        <motion.div
          animate={coverControls}
          initial={{ rotateY: 0 }}
          style={{
            position:           'absolute',
            inset:              0,
            borderRadius:       '3px 8px 8px 3px',
            background:         'linear-gradient(145deg, #0E2212 0%, #0A1A0E 55%, #081408 100%)',
            transformOrigin:    'left center',
            transformStyle:     'preserve-3d',
            backfaceVisibility: 'hidden',
            border:             '1px solid rgba(168,213,162,0.14)',
            boxShadow:          'inset -4px 0 16px rgba(0,0,0,0.5), 2px 2px 20px rgba(0,0,0,0.5)',
            overflow:           'hidden',
          }}
        >
          {/* Marco decorativo en tapa */}
          <div
            style={{
              position:     'absolute',
              inset:        '12px',
              border:       '1px solid rgba(168,213,162,0.10)',
              borderRadius: '2px',
            }}
          />

          {/* Título en tapa */}
          <div
            style={{
              position:      'absolute',
              inset:         0,
              display:       'flex',
              flexDirection: 'column',
              alignItems:    'center',
              justifyContent:'center',
              gap:           '8px',
            }}
          >
            <span
              style={{
                fontFamily:    '"Space Grotesk", sans-serif',
                fontWeight:    700,
                fontSize:      'clamp(14px, 2vw, 22px)',
                letterSpacing: '0.20em',
                color:         'rgba(249,250,251,0.75)',
                textTransform: 'uppercase',
                userSelect:    'none',
              }}
            >
              INDAGATA
            </span>
            <div
              style={{
                width:      '40%',
                height:     '1px',
                background: 'rgba(74,222,128,0.35)',
              }}
            />
            <span
              style={{
                fontFamily:    '"DM Mono", monospace',
                fontWeight:    400,
                fontSize:      'clamp(6px, 0.7vw, 8px)',
                letterSpacing: '0.18em',
                color:         'rgba(168,213,162,0.45)',
                textTransform: 'uppercase',
                userSelect:    'none',
              }}
            >
              Investigación · Educativa
            </span>
          </div>

          {/* Textura sutil de tapa */}
          <div
            style={{
              position:   'absolute',
              inset:      0,
              opacity:    0.04,
              background: `repeating-linear-gradient(
                135deg,
                transparent 0px,
                transparent 3px,
                rgba(168,213,162,0.5) 3px,
                rgba(168,213,162,0.5) 4px
              )`,
            }}
          />
        </motion.div>
      </motion.div>
    </motion.div>
  )
}
