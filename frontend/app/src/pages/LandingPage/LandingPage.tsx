/**
 * LandingPage.tsx
 * Página de inicio de INDAGATA - Landing con animación de hero
 * Integra los componentes del landing original con React Router
 */
import { useNavigate } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Imagen importada como módulo (Vite)
import vasconcelosImg from '../../assets/vasconcelos.jpg';

// Componentes del landing
import CustomCursor from './components/CustomCursor';
import DustParticles from './components/DustParticles';
import BookTransition from './components/BookTransition';

// ─── Easing ───────────────────────────────────────────────────────────────────
const EASE_OUT = [0.16, 1, 0.3, 1] as [number, number, number, number];
const EASE_IN = [0.4, 0, 1, 1] as [number, number, number, number];

// ─── Letras del logo ──────────────────────────────────────────────────────────
const LETTERS = 'INDAGATA'.split('');

// ─── Frase principal ──────────────────────────────────────────────────────────
const PHRASE = [
  { text: 'La investigación educativa', accent: false },
  { text: 'merece una plataforma', accent: false },
  { text: 'tan rigurosa como ella misma.', accent: true },
];

// ─── Timing (ms) ─────────────────────────────────────────────────────────────
const T = {
  LOGO_START: 900,
  LINE_APPEAR: 2800,
  LOGO_PAUSE: 3600,
  LOGO_EXIT: 4200,
  BOOK_START: 4600,
  BADGE_AFTER_PHRASE: 1800,
  CTA_AFTER_PHRASE: 2500,
  NAV_AFTER_PHRASE: 3200,
};

export default function LandingPage() {
  const navigate = useNavigate();

  const [photoBlurred, setPhotoBlurred] = useState(false);
  const [logoVisible, setLogoVisible] = useState(false);
  const [lineVisible, setLineVisible] = useState(false);
  const [bookVisible, setBookVisible] = useState(false);
  const [phraseVisible, setPhraseVisible] = useState(false);
  const [badgeVisible, setBadgeVisible] = useState(false);
  const [ctaVisible, setCtaVisible] = useState(false);
  const [navLogoVisible, setNavLogoVisible] = useState(false);
  const [introComplete, setIntroComplete] = useState(false);

  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const after = (ms: number, fn: () => void) => {
    const id = setTimeout(fn, ms);
    timers.current.push(id);
    return id;
  };

  const handleBookDone = () => {
    setPhraseVisible(true);
    setPhotoBlurred(false);
    after(T.BADGE_AFTER_PHRASE, () => setBadgeVisible(true));
    after(T.CTA_AFTER_PHRASE, () => setCtaVisible(true));
    after(T.NAV_AFTER_PHRASE, () => {
      setNavLogoVisible(true);
      setIntroComplete(true);
      sessionStorage.setItem('indagata_intro', '1');
    });
  };

  const handleEnterClick = () => {
    navigate('/login');
  };

  useEffect(() => {
    // Agregar clase al body para ocultar cursor nativo
    document.body.classList.add('landing-active');

    // Segunda visita — estado final directo
    if (sessionStorage.getItem('indagata_intro')) {
      setPhraseVisible(true);
      setBadgeVisible(true);
      setCtaVisible(true);
      setNavLogoVisible(true);
      setIntroComplete(true);
      return;
    }

    after(T.LOGO_START, () => setLogoVisible(true));
    after(T.LINE_APPEAR, () => setLineVisible(true));
    after(T.LOGO_EXIT, () => {
      setPhotoBlurred(true);
    });
    after(T.BOOK_START, () => {
      setLogoVisible(false);
      setBookVisible(true);
    });

    return () => {
      timers.current.forEach(clearTimeout);
      document.body.classList.remove('landing-active');
    };
  }, []);

  return (
    <div className="relative w-full h-screen overflow-hidden bg-[#060A07]">
      <CustomCursor />

      {/* ══ CAPA 1: Fotografía — Ken Burns ══════════════════════════════ */}
      <motion.div
        className="absolute inset-0"
        initial={{ opacity: 0, filter: 'blur(18px)', scale: 1.0 }}
        animate={{
          opacity: 1,
          filter: photoBlurred ? 'blur(7px)' : 'blur(0px)',
          scale: 1.08,
        }}
        transition={{
          opacity: { duration: 1.7, ease: 'easeOut' },
          filter: { duration: 0.9, ease: 'easeInOut' },
          scale: { duration: 24, ease: 'linear' },
        }}
        style={{ transformOrigin: 'center center' }}
      >
        <img
          src={vasconcelosImg}
          alt=""
          aria-hidden="true"
          className="w-full h-full object-cover"
          draggable="false"
        />
      </motion.div>

      {/* ══ CAPA 2: Overlay de oscurecimiento ═══════════════════════════ */}
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
                y: -50,
                opacity: 0,
                filter: 'blur(6px)',
                transition: { duration: 0.85, ease: EASE_IN },
              }}
            >
              <div aria-label="INDAGATA" style={{ display: 'flex', alignItems: 'center' }}>
                {LETTERS.map((letter, i) => (
                  <motion.span
                    key={i}
                    style={{
                      fontFamily: '"Space Grotesk", sans-serif',
                      fontWeight: 700,
                      letterSpacing: '0.17em',
                      textTransform: 'uppercase',
                      fontSize: 'clamp(46px, 8.2vw, 106px)',
                      lineHeight: 1,
                      display: 'inline-block',
                      color: '#F9FAFB',
                      userSelect: 'none',
                    }}
                    initial={{ y: 50, opacity: 0, filter: 'blur(10px)' }}
                    animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
                    transition={{
                      delay: i * 0.14,
                      duration: 0.9,
                      ease: EASE_OUT,
                    }}
                  >
                    {letter}
                  </motion.span>
                ))}
              </div>

              <AnimatePresence>
                {lineVisible && (
                  <motion.div
                    key="line"
                    style={{
                      height: '1px',
                      width: 'clamp(130px, 24vw, 340px)',
                      background: '#4ADE80',
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
        {bookVisible && <BookTransition key="book" onDone={handleBookDone} />}
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
              {PHRASE.map((line, i) => (
                <motion.p
                  key={i}
                  style={{
                    fontFamily: '"Cormorant Garamond", serif',
                    fontWeight: 600,
                    fontStyle: 'italic',
                    fontSize: 'clamp(26px, 4.6vw, 64px)',
                    lineHeight: 1.18,
                    color: line.accent ? '#4ADE80' : '#F9FAFB',
                    userSelect: 'none',
                  }}
                  initial={{ y: 28, opacity: 0, filter: 'blur(12px)' }}
                  animate={{ y: 0, opacity: 1, filter: 'blur(0px)' }}
                  transition={{
                    delay: i * 0.26,
                    duration: 0.9,
                    ease: EASE_OUT,
                  }}
                >
                  {line.text}
                </motion.p>
              ))}

              <motion.p
                style={{
                  fontFamily: '"Inter", sans-serif',
                  fontWeight: 400,
                  fontSize: 'clamp(11px, 1.3vw, 15px)',
                  letterSpacing: '0.045em',
                  color: '#9CA3AF',
                  marginTop: '16px',
                  userSelect: 'none',
                }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.88, duration: 0.65, ease: 'easeOut' }}
              >
                Gestión inteligente de instrumentos de investigación educativa.
              </motion.p>

              <AnimatePresence>
                {badgeVisible && (
                  <motion.div
                    key="badge"
                    style={{
                      fontFamily: '"DM Mono", monospace',
                      fontSize: '10px',
                      letterSpacing: '0.13em',
                      color: '#A8D5A2',
                      marginTop: '14px',
                      padding: '7px 18px',
                      borderRadius: '100px',
                      border: '1px solid rgba(168,213,162,0.16)',
                      background: 'rgba(18,26,20,0.52)',
                      backdropFilter: 'blur(14px)',
                      userSelect: 'none',
                    }}
                    initial={{ opacity: 0, scale: 0.93 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.55, ease: EASE_OUT }}
                  >
                    RAG · IA · KPIs EDUCATIVOS
                  </motion.div>
                )}
              </AnimatePresence>

              <AnimatePresence>
                {ctaVisible && (
                  <motion.div
                    key="cta"
                    className="relative flex items-center justify-center"
                    style={{ marginTop: '38px' }}
                    initial={{ y: 30, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ type: 'spring', damping: 20, stiffness: 155 }}
                  >
                    {[0, 1.25].map((delay, i) => (
                      <motion.span
                        key={i}
                        className="absolute rounded-lg pointer-events-none"
                        style={{
                          inset: '-6px -12px',
                          border: '1px solid rgba(74,222,128,0.38)',
                        }}
                        animate={{
                          scale: [1, 1.13, 1.24],
                          opacity: [0.48, 0.18, 0],
                        }}
                        transition={{
                          duration: 2.5,
                          delay,
                          repeat: Infinity,
                          ease: 'easeOut',
                        }}
                      />
                    ))}

                    <motion.button
                      onClick={handleEnterClick}
                      style={{
                        fontFamily: '"Inter", sans-serif',
                        fontWeight: 500,
                        fontSize: 'clamp(13px, 1.15vw, 15px)',
                        letterSpacing: '0.025em',
                        padding: '15px 46px',
                        borderRadius: '8px',
                        border: 'none',
                        background: '#4ADE80',
                        color: '#060A07',
                        cursor: 'pointer',
                        position: 'relative',
                        zIndex: 1,
                        userSelect: 'none',
                      }}
                      whileHover={{
                        scale: 1.04,
                        background: '#86EFAC',
                        boxShadow: '0 0 30px rgba(74,222,128,0.26), 0 0 8px rgba(74,222,128,0.12)',
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
                fontFamily: '"Space Grotesk", sans-serif',
                fontWeight: 700,
                fontSize: '17px',
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                color: '#F9FAFB',
                userSelect: 'none',
              }}
            >
              INDAGATA
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══ Indicador de espera ═════════════════════════════════════════ */}
      <AnimatePresence>
        {logoVisible && !bookVisible && (
          <motion.div
            className="absolute z-10"
            style={{
              bottom: '30px',
              left: '50%',
              transform: 'translateX(-50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.4 }}
            exit={{ opacity: 0, transition: { duration: 0.3 } }}
            transition={{ duration: 0.7, delay: 1.0 }}
          >
            <div
              style={{
                width: '1px',
                height: '40px',
                background: 'rgba(168,213,162,0.32)',
                position: 'relative',
                overflow: 'hidden',
                borderRadius: '2px',
              }}
            >
              <motion.div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '36%',
                  background: '#4ADE80',
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
  );
}
