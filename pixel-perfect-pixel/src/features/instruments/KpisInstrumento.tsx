import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { getKpisDeInstrumento } from "@/api/instrumentos";
import type { KpiDeInstrumento } from "@/types";

interface KpisInstrumentoProps {
  instrumentoId: string;
}

/** KPIs del instrumento y las preguntas que mejor miden cada uno. */
export function KpisInstrumento({ instrumentoId }: KpisInstrumentoProps) {
  const [kpis, setKpis] = useState<KpiDeInstrumento[] | null>(null);

  useEffect(() => {
    let vigente = true;
    setKpis(null);
    getKpisDeInstrumento(instrumentoId)
      .then((k) => vigente && setKpis(k))
      .catch(() => vigente && setKpis([]));
    return () => {
      vigente = false;
    };
  }, [instrumentoId]);

  if (kpis === null) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Cargando KPIs…
      </p>
    );
  }
  if (kpis.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin KPIs asociados todavía.</p>;
  }
  return (
    <ul className="space-y-3">
      {kpis.map((k) => (
        <li key={k.kpiId} className="space-y-1.5 rounded-lg border px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium">{k.nombre}</span>
            <span className="text-[11px] text-muted-foreground">
              {k.origen === "aceptado" ? "Aceptado por su autor" : "Referencia de diseño"}
              {k.score != null && ` · ${Math.round(k.score * 100)}%`}
            </span>
          </div>
          {k.preguntas.length > 0 && (
            <ol className="space-y-1">
              {k.preguntas.map((p) => (
                <li key={p.preguntaId || p.texto} className="flex items-start gap-2 text-xs">
                  <span className="mt-0.5 shrink-0 rounded bg-primary/10 px-1.5 font-mono text-primary">
                    {Math.round(p.score * 100)}%
                  </span>
                  <span className="text-foreground/80">{p.texto}</span>
                </li>
              ))}
            </ol>
          )}
        </li>
      ))}
    </ul>
  );
}
