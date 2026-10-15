import { AlertTriangle, Magnet, Ruler, SplitSquareHorizontal } from "lucide-react";

interface ComoLeerMapaProps {
  /** Proporción de varianza explicada por PC1 + PC2 (0–1). */
  varianzaTotal: number;
  varianzaBaja: boolean;
  /** KPIs e instrumentos ocupan regiones separadas del eje PC1. */
  brecha: boolean;
}

function porcentaje(v: number) {
  return `${(v * 100).toLocaleString("es-MX", { maximumFractionDigits: 0 })} %`;
}

/** Guía breve para interpretar el mapa sin conocimientos de embeddings. */
export function ComoLeerMapa({ varianzaTotal, varianzaBaja, brecha }: ComoLeerMapaProps) {
  return (
    <ul className="space-y-4 text-sm leading-relaxed text-muted-foreground">
      <li className="flex gap-3">
        <Magnet className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
        <span>
          <strong className="text-foreground">Cerca = significado parecido.</strong> Cada punto es
          un texto convertido en un vector de 768 números; los que tratan temas similares quedan
          próximos. Es la misma medida que usa el chat para encontrar fuentes.
        </span>
      </li>
      <li className="flex gap-3">
        <Ruler className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
        <span>
          <strong className="text-foreground">Es una aproximación en 2D.</strong> Los ejes son las
          dos direcciones que más diferencian a los textos (componentes principales) y conservan el{" "}
          <strong className="text-foreground">{porcentaje(varianzaTotal)}</strong> de la
          información. Las similitudes exactas se calculan en el espacio completo.
        </span>
      </li>
      {varianzaBaja && (
        <li className="flex gap-3 rounded-2xl bg-accent-soft p-3 text-accent-foreground">
          <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden />
          <span>
            El plano conserva poca información: toma las distancias como orientación general, no
            como medida.
          </span>
        </li>
      )}
      {brecha && (
        <li className="flex gap-3">
          <SplitSquareHorizontal className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
          <span>
            <strong className="text-foreground">Dos regiones.</strong> Los KPIs (definiciones) y los
            instrumentos (cuestionarios) se escriben de forma muy distinta, y esa diferencia domina
            el eje horizontal. Compara posiciones dentro de cada grupo; la relación KPI ↔
            instrumento se mide con su similitud.
          </span>
        </li>
      )}
    </ul>
  );
}
