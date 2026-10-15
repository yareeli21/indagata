import type { ReactNode } from "react";
import { motion, type Variants } from "motion/react";

const CONTENEDOR: Variants = {
  oculto: {},
  visible: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

const ELEMENTO: Variants = {
  oculto: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } },
};

interface AparecerProps {
  children: ReactNode;
  className?: string | undefined;
}

/** Contenedor que hace aparecer a sus `AparecerItem` de forma escalonada. */
export function Aparecer({ children, className }: AparecerProps) {
  return (
    <motion.div
      className={className}
      variants={CONTENEDOR}
      initial="oculto"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
    >
      {children}
    </motion.div>
  );
}

/** Elemento hijo de `Aparecer`: entra con fade + desplazamiento vertical. */
export function AparecerItem({ children, className }: AparecerProps) {
  return (
    <motion.div className={className} variants={ELEMENTO}>
      {children}
    </motion.div>
  );
}
