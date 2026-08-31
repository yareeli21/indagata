import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import DustParticles from './DustParticles'
import BookTransition from './BookTransition'

// ─── Placeholder SVG de biblioteca ───────────────────────────────────────────
// Reemplazar src={PLACEHOLDER_BG} por src="/src/assets/vasconcelos.jpg"
const PLACEHOLDER_BG = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0.5" y2="1">
      <stop offset="0%"   stop-color="#060A07"/>
      <stop offset="55%"  stop-color="#0B1510"/>
      <stop offset="100%" stop-color="#122018"/>
    </linearGradient>
    <radialGradient id="g1" cx="18%" cy="14%" r="38%">
      <stop offset="0%"   stop-color="#285530" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#060A07" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="g2" cx="82%" cy="38%" r="28%">
      <stop offset="0%"   stop-color="#1C4428" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="#060A07" stop-opacity="0"/>
    </radialGradient>
    <filter id="s"><feGaussianBlur stdDeviation="1.8"/></filter>
  </defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <rect width="1920" height="1080" fill="url(#g1)"/>
  <rect width="1920" height="1080" fill="url(#g2)"/>
  <g filter="url(#s)" opacity="0.38">
    <rect x="72"  y="155" width="20" height="172" rx="2" fill="#2A4C28"/>
    <rect x="96"  y="172" width="16" height="155" rx="2" fill="#1C3A20"/>
    <rect x="116" y="150" width="24" height="177" rx="2" fill="#345435"/>
    <rect x="144" y="168" width="18" height="160" rx="2" fill="#264628"/>
    <rect x="166" y="158" width="22" height="170" rx="2" fill="#1E3E20"/>
    <rect x="192" y="176" width="14" height="152" rx="2" fill="#2E5432"/>
    <rect x="210" y="153" width="26" height="174" rx="2" fill="#38583A"/>
    <rect x="240" y="170" width="18" height="158" rx="2" fill="#224424"/>
    <rect x="262" y="160" width="20" height="168" rx="2" fill="#3A6240"/>
    <rect x="288" y="172" width="16" height="156" rx="2" fill="#284A28"/>
    <rect x="55"  y="329" width="280" height="7" rx="1" fill="#122018"/>
    <rect x="1490" y="135" width="22" height="185" rx="2" fill="#284A2A"/>
    <rect x="1516" y="155" width="18" height="165" rx="2" fill="#1E3E20"/>
    <rect x="1538" y="143" width="26" height="177" rx="2" fill="#325435"/>
    <rect x="1568" y="158" width="20" height="162" rx="2" fill="#244624"/>
    <rect x="1592" y="145" width="22" height="175" rx="2" fill="#1A3C1C"/>
    <rect x="1618" y="162" width="16" height="158" rx="2" fill="#2E542E"/>
    <rect x="1638" y="138" width="24" height="182" rx="2" fill="#365838"/>
    <rect x="1476" y="320" width="220" height="7" rx="1" fill="#122018"/>
  </g>
  <g opacity="0.18">
    <rect x="590" y="575" width="740" height="430" rx="4" fill="#0A1208"/>
    <rect x="626" y="596" width="295" height="215" rx="3" fill="#0C1C0C"/>
    <rect x="628" y="598" width="145" height="211" rx="2" fill="#0E1E0E"/>
    <rect x="773" y="598" width="146" height="211" rx="2" fill="#101E10"/>
    <rect x="638" y="618" width="126" height="2" rx="1" fill="#1E3A1E" opacity="0.65"/>
    <rect x="638" y="630" width="113" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
    <rect x="638" y="642" width="118" height="2" rx="1" fill="#1E3A1E" opacity="0.6"/>
    <rect x="638" y="654" width="106" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
    <rect x="783" y="618" width="126" height="2" rx="1" fill="#1E3A1E" opacity="0.65"/>
    <rect x="783" y="630" width="116" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
    <rect x="783" y="642" width="120" height="2" rx="1" fill="#1E3A1E" opacity="0.6"/>
    <rect x="783" y="654" width="108" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
    <rect x="966" y="606" width="195" height="165" rx="3" fill="#0C1C0C"/>
    <rect x="977" y="622" width="172" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
    <rect x="977" y="636" width="158" height="2" rx="1" fill="#1E3A1E" opacity="0.4"/>
    <rect x="977" y="650" width="165" height="2" rx="1" fill="#1E3A1E" opacity="0.5"/>
  </g>
  <text x="960" y="486" text-anchor="middle" fill="#244224"
        font-size="14" font-family="monospace" opacity="0.45">
    [ Reemplazar con fotografía — src/assets/vasconcelos.jpg ]
  </text>
</svg>
`)}`

// ─── Easing ───────────────────────────────────────────────────────────────────
const EASE_OUT  = [0.16, 1, 0.3, 1]
const EASE_IN   = [0.4, 0, 1, 1]

// ─── Letras del logo ──────────────────────────────────────────────────────────
const LETTERS = 'INDAGATA'.split('')

// ─── Frase principal ──────────────────────────────────────────────────────────
const PHRASE = [
  { text: 'La investigación educativa',     accent: false },
  { text: 'merece una plataforma',          accent: false },
  { text: 'tan rigurosa como ella misma.',  accent: true  },
]

// ─── Timing (ms) ─────────────────────────────────────────────────────────────
//  Las letras del logo aparecen lento (stagger 140ms c/u = ~1.1s total)
//  Luego una pausa, después el libro, después la frase.
const T = {
  LOGO_START:     900,   // Empieza el stagger de letras
  LINE_APPEAR:   2800,   // Línea verde aparece
  LOGO_PAUSE:    3600,   // INDAGATA visible completo — pausa dramática
  LOGO_EXIT:     4200,   // Logo hace fade-up lento y sale
  BOOK_START:    4600,   // Libro entra al centro de pantalla
  // BookTransition maneja su propio timing interno (~3.2s total animación)
  // onDone() se llama al terminar → dispara PHRASE_START
  BADGE_AFTER_PHRASE: 1800,  // ms después de que phraseVisible = true
  CTA_AFTER_PHRASE:   2500,
  NAV_AFTER_PHRASE:   3200,
}

// ─────────────────────────────────────────────────────────────────────────────
export default function HeroSequence() {

  const [photoBlurred,   setPhotoBlurred]   = useState(false)
  const [logoVisible,    setLogoVisible]    = useState(false)
  const [lineVisible,    setLineVisible]    = useState(false)
  const [bookVisible,    setBookVisible]    = useState(false)
  const [phraseVisible,  setPhraseVisible]  = useState(false)
  const [badgeVisible,   setBadgeVisible]   = useState(false)
  const [ctaVisible,     setCtaVisible]     = useState(false)
  const [navLogoVisible, setNavLogoVisible] = useState(false)
  const [introComplete,  setIntroComplete]  = useState(false)

  const timers = useRef([])
  const after  = (ms, fn) => {
    const id = setTimeout(fn, ms)
    timers.current.push(id)
    return id
  }

  // Callback que dispara la frase cuando el libro termina
  const handleBookDone = () => {
    setPhraseVisible(true)
    setPhotoBlurred(false)
    after(T.BADGE_AFTER_PHRASE, () => setBadgeVisible(true))
    after(T.CTA_AFTER_PHRASE,   () => setCtaVisible(true))
    after(T.NAV_AFTER_PHRASE,   () => {
      setNavLogoVisible(true)
      setIntroComplete(true)
      sessionStorage.setItem('indagata_intro', '1')
    })
  }

  useEffect(() => {
    // Segunda visita — estado final directo
    if (sessionStorage.getItem('indagata_intro')) {
      setPhraseVisible(true)
      setBadgeVisible(true)
      setCtaVisible(true)
      setNavLogoVisible(true)
      setIntroComplete(true)
      return
    }

    after(T.LOGO_START,  () => setLogoVisible(true))
    after(T.LINE_APPEAR, () => setLineVisible(true))
    after(T.LOGO_EXIT,   () => { setPhotoBlurred(true) })
    after(T.BOOK_START,  () => { setLogoVisible(false); setBookVisible(true) })

    return () => timers.current.forEach(clearTimeout)
  }, [])

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#060A07]">

      {/* ══ CAPA 1: Fotografía — Ken Burns ══════════════════════════════ */}
      <motion.div
        className="absolute inset-0"
        initial={{ opacity: 0, filter: 'blur(18px)', scale: 1.0 }}
        animate={{
          opacity: 1,
          filter:  photoBlurred ? 'blur(7px)' : 'blur(0px)',
          scale:   1.08,
        }}
        transition={{
          opacity: { duration: 1.7, ease: 'easeOut' },
          filter:  { duration: 0.9, ease: 'easeInOut' },
          scale:   { duration: 24, ease: 'linear' },
        }}
        style={{ transformOrigin: 'center center' }}
      >
        {/*
          ── Para usar tu foto real reemplaza src={PLACEHOLDER_BG} por: ──
             src="/src/assets/vasconcelos.jpg"
          ── y elimina la constante PLACEHOLDER_BG de arriba ──────────────
        */}
        <img
          src="/src/assets/vasconcelos.jpg"
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover"
          draggable="false"
        />
      </motion.div>

      {/* ══ CAPA 2: Overlay de oscurecimiento (durante libro) ═══════════ */}
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ zIndex: 2, background: 'rgba(4,8,5,0.52)' }}
        animate={{ opacity: photoBlurred ? 1 : 0 }}
        transition={{ duration: 0.7, ease: 'easeInOut' }}
      />

      {/* ══ CAPA 3: Gradiente permanente ════════════════════════════════ */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          zIndex: 3,
          background: `linear-gradient(
            to bottom,
            rgba(6,10,7,0.40) 0%,
            rgba(6,10,7,0.56) 45%,
            rgba(6,10,7,0.90) 100%
          )`,
        }}
      />

      {/* ══ CAPA 4: Partículas de polvo ═════════════════════════════════ */}
      <DustParticles opacity={introComplete ? 0.75 : 0.45} />

      {/* ══ CAPA 5: Logo INDAGATA ════════════════════════════════════════ */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ zIndex: 10 }}
      >
        <AnimatePresence mode="wait">
          {logoVisible && (
            <motion.div
              key="logo"
              className="flex flex-col items-center"
              style={{ gap: '22px' }}
              exit={{
                y:       -50,
                opacity:  0,
                filter:  'blur(6px)',
                transition: { duration: 0.85, ease: EASE_IN },
              }}
            >
              {/* Letras — stagger lento 140ms c/u */}
              <div aria-label="INDAGATA" style={{ display: 'flex', alignItems: 'center' }}>
                {LETTERS.map((letter, i) => (
                  <motion.span
                    key={i}
                    style={{
                      fontFamily:    '"Space Grotesk", sans-serif',
                      fontWeight:    700,
                      letterSpacing: '0.17em',
                      textTransform: 'uppercase',
                      fontSize:      'clamp(46px, 8.2vw, 106px)',
                      lineHeight:    1,
                      display:       'inline-block',
                      color:         '#F9FAFB',
                      userSelect:    'none',
                    }}
                    initial={{ y: 50, opacity: 0, filter: 'blur(10px)' }}
                    animate={{ y: 0,  opacity: 1, filter: 'blur(0px)' }}
                    transition={{
                      delay:    i * 0.14,   // 140ms por letra = ~1.1s total
                      duration: 0.90,
                      ease:     EASE_OUT,
                    }}
                  >
                    {letter}
                  </motion.span>
                ))}
              </div>

              {/* Línea verde bajo el logo */}
              <AnimatePresence>
                {lineVisible && (
                  <motion.div
                    key="line"
                    style={{
                      height:          '1px',
                      width:           'clamp(130px, 24vw, 340px)',
                      background:      '#4ADE80',
                      transformOrigin: 'left center',
                    }}
                    initial={{ scaleX: 0, opacity: 1 }}
                    animate={{ scaleX: 1, opacity: 1 }}
                    exit={{
                      scaleX: 0,
                      opacity: 0,
                      transformOrigin: 'center',
                      transition: { duration: 0.4, ease: EASE_IN },
                    }}
                    transition={{ duration: 0.75, ease: EASE_OUT }}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ══ CAPA 6: Libro animado ════════════════════════════════════════ */}
      <AnimatePresence>
        {bookVisible && (
          <BookTransition
            key="book"
            onDone={handleBookDone}
          />
        )}
      </AnimatePresence>

      {/* ══ CAPA 7: Frase + badge + CTA ═════════════════════════════════ */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center px-6"
        style={{ zIndex: 10 }}
      >
        <AnimatePresence>
          {phraseVisible && (
            <motion.div
              key="phrase"
              className="flex flex-col items-center text-center"
              style={{ gap: '4px' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              {/* Líneas de la frase — blur-to-sharp + elevación */}
              {PHRASE.map((line, i) => (
                <motion.p
                  key={i}
                  style={{
                    fontFamily: '"Cormorant Garamond", serif',
                    fontWeight: 600,
                    fontStyle:  'italic',
                    fontSize:   'clamp(26px, 4.6vw, 64px)',
                    lineHeight: 1.18,
                    color:      line.accent ? '#4ADE80' : '#F9FAFB',
                    userSelect: 'none',
                  }}
                  initial={{ y: 28, opacity: 0, filter: 'blur(12px)' }}
                  animate={{ y: 0,  opacity: 1, filter: 'blur(0px)'  }}
                  transition={{
                    delay:    i * 0.26,
                    duration: 0.9,
                    ease:     EASE_OUT,
                  }}
                >
                  {line.text}
                </motion.p>
              ))}

              {/* Tagline */}
              <motion.p
                style={{
                  fontFamily:    '"Inter", sans-serif',
                  fontWeight:    400,
                  fontSize:      'clamp(11px, 1.3vw, 15px)',
                  letterSpacing: '0.045em',
                  color:         '#9CA3AF',
                  marginTop:     '16px',
                  userSelect:    'none',
                }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0  }}
                transition={{ delay: 0.88, duration: 0.65, ease: 'easeOut' }}
              >
                Gestión inteligente de instrumentos de investigación educativa.
              </motion.p>

              {/* Badge tecnológico */}
              <AnimatePresence>
                {badgeVisible && (
                  <motion.div
                    key="badge"
                    style={{
                      fontFamily:     '"DM Mono", monospace',
                      fontSize:       '10px',
                      letterSpacing:  '0.13em',
                      color:          '#A8D5A2',
                      marginTop:      '14px',
                      padding:        '7px 18px',
                      borderRadius:   '100px',
                      border:         '1px solid rgba(168,213,162,0.16)',
                      background:     'rgba(18,26,20,0.52)',
                      backdropFilter: 'blur(14px)',
                      userSelect:     'none',
                    }}
                    initial={{ opacity: 0, scale: 0.93 }}
                    animate={{ opacity: 1, scale: 1    }}
                    transition={{ duration: 0.55, ease: EASE_OUT }}
                  >
                    RAG · IA · KPIs EDUCATIVOS
                  </motion.div>
                )}
              </AnimatePresence>

              {/* CTA con anillo pulsante */}
              <AnimatePresence>
                {ctaVisible && (
                  <motion.div
                    key="cta"
                    className="relative flex items-center justify-center"
                    style={{ marginTop: '38px' }}
                    initial={{ y: 30, opacity: 0 }}
                    animate={{ y: 0,  opacity: 1 }}
                    transition={{ type: 'spring', damping: 20, stiffness: 155 }}
                  >
                    {/* Ondas pulsantes — dos desfasadas */}
                    {[0, 1.25].map((delay, i) => (
                      <motion.span
                        key={i}
                        className="absolute rounded-lg pointer-events-none"
                        style={{
                          inset:  '-6px -12px',
                          border: '1px solid rgba(74,222,128,0.38)',
                        }}
                        animate={{
                          scale:   [1, 1.13, 1.24],
                          opacity: [0.48, 0.18, 0],
                        }}
                        transition={{
                          duration: 2.5,
                          delay,
                          repeat:   Infinity,
                          ease:     'easeOut',
                        }}
                      />
                    ))}

                    {/* Botón */}
                    <motion.button
                      onClick={() => { window.location.href = '/login' }}
                      style={{
                        fontFamily:    '"Inter", sans-serif',
                        fontWeight:    500,
                        fontSize:      'clamp(13px, 1.15vw, 15px)',
                        letterSpacing: '0.025em',
                        padding:       '15px 46px',
                        borderRadius:  '8px',
                        border:        'none',
                        background:    '#4ADE80',
                        color:         '#060A07',
                        cursor:        'pointer',
                        position:      'relative',
                        zIndex:        1,
                        userSelect:    'none',
                      }}
                      whileHover={{
                        scale:      1.04,
                        background: '#86EFAC',
                        boxShadow:  '0 0 30px rgba(74,222,128,0.26), 0 0 8px rgba(74,222,128,0.12)',
                        transition: { duration: 0.2 },
                      }}
                      whileTap={{ scale: 0.97 }}
                    >
                      Ingresar a Indagata →
                    </motion.button>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ══ CAPA 8: Nav logo ════════════════════════════════════════════ */}
      <AnimatePresence>
        {navLogoVisible && (
          <motion.div
            className="absolute z-20"
            style={{ top: '28px', left: '36px' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1.1, ease: 'easeOut' }}
          >
            <span
              style={{
                fontFamily:    '"Space Grotesk", sans-serif',
                fontWeight:    700,
                fontSize:      '17px',
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color:         '#F9FAFB',
                userSelect:    'none',
              }}
            >
              INDAGATA
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ Indicador de espera (durante logo, antes del libro) ═════════ */}
      <AnimatePresence>
        {logoVisible && !bookVisible && (
          <motion.div
            className="absolute z-10"
            style={{
              bottom:         '30px',
              left:           '50%',
              transform:      'translateX(-50%)',
              display:        'flex',
              flexDirection:  'column',
              alignItems:     'center',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4  }}
            exit={{ opacity: 0, transition: { duration: 0.3 } }}
            transition={{ duration: 0.7, delay: 1.0 }}
          >
            <div
              style={{
                width:        '1px',
                height:       '40px',
                background:   'rgba(168,213,162,0.32)',
                position:     'relative',
                overflow:     'hidden',
                borderRadius: '2px',
              }}
            >
              <motion.div
                style={{
                  position:     'absolute',
                  top:          0,
                  left:         0,
                  width:        '100%',
                  height:       '36%',
                  background:   '#4ADE80',
                  borderRadius: '2px',
                }}
                animate={{ y: [0, 26, 0] }}
                transition={{ duration: 1.9, repeat: Infinity, ease: 'easeInOut' }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
