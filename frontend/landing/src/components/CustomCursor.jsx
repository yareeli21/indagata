import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'

/**
 * CustomCursor
 * Punto verde que sigue al mouse con spring physics.
 * En hover sobre elementos interactivos crece con un anillo exterior.
 */
export default function CustomCursor() {
  const cursorX = useMotionValue(-100)
  const cursorY = useMotionValue(-100)
  const isHovering = useRef(false)

  // Spring suave para el punto central
  const springConfig = { damping: 28, stiffness: 350, mass: 0.5 }
  const x = useSpring(cursorX, springConfig)
  const y = useSpring(cursorY, springConfig)

  // Spring más lento para el anillo exterior (lag intencional)
  const ringSpring = { damping: 22, stiffness: 200, mass: 0.8 }
  const ringX = useSpring(cursorX, ringSpring)
  const ringY = useSpring(cursorY, ringSpring)

  useEffect(() => {
    const moveCursor = (e) => {
      cursorX.set(e.clientX)
      cursorY.set(e.clientY)
    }

    const handleMouseEnter = () => { isHovering.current = true }
    const handleMouseLeave = () => { isHovering.current = false }

    window.addEventListener('mousemove', moveCursor)

    // Detectar hover sobre elementos interactivos
    const interactives = document.querySelectorAll('a, button, [role="button"]')
    interactives.forEach(el => {
      el.addEventListener('mouseenter', handleMouseEnter)
      el.addEventListener('mouseleave', handleMouseLeave)
    })

    return () => {
      window.removeEventListener('mousemove', moveCursor)
      interactives.forEach(el => {
        el.removeEventListener('mouseenter', handleMouseEnter)
        el.removeEventListener('mouseleave', handleMouseLeave)
      })
    }
  }, [cursorX, cursorY])

  return (
    <>
      {/* Anillo exterior — lag mayor */}
      <motion.div
        className="fixed top-0 left-0 pointer-events-none z-[9998]"
        style={{
          x: ringX,
          y: ringY,
          translateX: '-50%',
          translateY: '-50%',
        }}
      >
        <motion.div
          className="rounded-full border border-green-vivid"
          animate={{
            width:   isHovering.current ? 40 : 28,
            height:  isHovering.current ? 40 : 28,
            opacity: isHovering.current ? 0.5 : 0.2,
          }}
          transition={{ duration: 0.2 }}
          style={{ width: 28, height: 28 }}
        />
      </motion.div>

      {/* Punto central — respuesta rápida */}
      <motion.div
        className="fixed top-0 left-0 pointer-events-none z-[9998]"
        style={{
          x,
          y,
          translateX: '-50%',
          translateY: '-50%',
        }}
      >
        <motion.div
          className="rounded-full bg-green-neon"
          animate={{
            width:  isHovering.current ? 6 : 7,
            height: isHovering.current ? 6 : 7,
          }}
          transition={{ duration: 0.15 }}
          style={{ width: 7, height: 7 }}
        />
      </motion.div>
    </>
  )
}
