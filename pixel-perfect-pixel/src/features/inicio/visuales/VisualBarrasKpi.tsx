import { motion } from "motion/react";
import { GridPattern } from "@/components/efectos/GridPattern";

export interface BarraKpi {
  nombre: string;
  total: number;
}

// Forma de respaldo mientras no hay instrumentos con KPIs.
const RESPALDO: BarraKpi[] = [4, 7, 5, 9, 6, 8].map((total, i) => ({ nombre: `kpi-${i}`, total }));

/** Barras animadas con los KPIs más medidos del acervo (fondo del gateway KPIs). */
export function VisualBarrasKpi({ barras }: { barras: BarraKpi[] }) {
  const datos = barras.length > 0 ? barras : RESPALDO;
  const maximo = Math.max(1, ...datos.map((b) => b.total));
  return (
    <>
      <GridPattern className="text-hero-foreground/[0.06]" tamano={32} />
      <div className="absolute inset-x-6 bottom-48 top-28 flex items-end gap-2 md:inset-x-7 md:gap-3">
        {datos.map((b, i) => (
          <motion.div
            key={b.nombre}
            className="flex-1 rounded-t-xl bg-gradient-to-t from-accent/20 to-accent"
            initial={{ height: "8%" }}
            whileInView={{ height: `${Math.max(12, (b.total / maximo) * 100)}%` }}
            viewport={{ once: true }}
            transition={{ duration: 0.9, delay: 0.1 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
          />
        ))}
      </div>
    </>
  );
}
