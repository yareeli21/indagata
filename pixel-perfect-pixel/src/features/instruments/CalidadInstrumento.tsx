import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Info,
  Lightbulb,
  ShieldAlert,
} from "lucide-react";
import { getResumenLimpieza } from "@/api/limpieza";
import type { ErrorHttp } from "@/api/client";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { EstadisticaLimpieza } from "@/features/upload/limpieza/estadistica/EstadisticaLimpieza";
import { cn } from "@/lib/utils";
import type { ResumenLimpieza, SugerenciaAnalisis } from "@/types";

const ICONO: Record<SugerenciaAnalisis["nivel"], typeof Info> = {
  bien: CheckCircle2,
  info: Info,
  atencion: AlertTriangle,
  alerta: ShieldAlert,
};
const TONO: Record<SugerenciaAnalisis["nivel"], string> = {
  bien: "text-success",
  info: "text-primary",
  atencion: "text-accent-strong",
  alerta: "text-destructive",
};

interface CalidadInstrumentoProps {
  instrumentoId: string;
}

/**
 * Medidas estadísticas de la limpieza y sugerencias de análisis, para consultarlas
 * después de guardar el instrumento. Se cargan al abrir el bloque.
 */
export function CalidadInstrumento({ instrumentoId }: CalidadInstrumentoProps) {
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState<ResumenLimpieza | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    setDatos(null);
    setAviso(null);
    setAbierto(false);
  }, [instrumentoId]);

  useEffect(() => {
    if (!abierto || datos || aviso || !/^\d+$/.test(instrumentoId)) return;
    let vigente = true;
    setCargando(true);
    getResumenLimpieza(Number(instrumentoId))
      .then((r) => vigente && setDatos(r))
      .catch((e: ErrorHttp) => {
        if (!vigente) return;
        setAviso(
          e.status === 404
            ? "Este instrumento no pasó por la limpieza asistida (se cargó antes de ese paso)."
            : e.status === 403
              ? "Las medidas se podrán ver cuando su autor apruebe el instrumento."
              : "No se pudieron cargar las medidas de la limpieza.",
        );
      })
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [abierto, datos, aviso, instrumentoId]);

  return (
    <Collapsible
      open={abierto}
      onOpenChange={setAbierto}
      className="rounded-2xl border border-border"
    >
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-semibold text-foreground">
        <span className="flex items-center gap-2">
          <Lightbulb className="size-4 text-primary" aria-hidden />
          Calidad de los datos y sugerencias de análisis
        </span>
        <ChevronDown
          className={cn("size-4 transition-transform", abierto && "rotate-180")}
          aria-hidden
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-4 border-t border-border px-4 py-4">
        {cargando && <p className="text-sm text-muted-foreground">Cargando medidas…</p>}
        {aviso && <p className="text-sm text-muted-foreground">{aviso}</p>}
        {datos && (
          <>
            {datos.sugerencias.length > 0 && (
              <section className="space-y-2">
                <h3 className="text-sm font-bold text-foreground">Sugerencias de análisis</h3>
                <ul className="space-y-2">
                  {datos.sugerencias.map((s) => {
                    const Icono = ICONO[s.nivel];
                    return (
                      <li key={s.texto} className="flex gap-2 text-sm">
                        <Icono
                          className={cn("mt-0.5 size-4 shrink-0", TONO[s.nivel])}
                          aria-hidden
                        />
                        <span>
                          <span className="text-foreground">{s.texto}</span>{" "}
                          <span className="text-muted-foreground">{s.porque}</span>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </section>
            )}
            {datos.cifras.length > 0 && (
              <dl className="grid grid-cols-2 gap-2">
                {datos.cifras.map((c) => (
                  <div key={c.etiqueta} className="rounded-xl bg-muted/40 px-3 py-2">
                    <dt className="text-xs text-muted-foreground">{c.etiqueta}</dt>
                    <dd className="font-display text-lg font-bold tabular-nums text-primary">
                      {c.valor}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            <EstadisticaLimpieza
              despues={datos.estadistica}
              antes={datos.estadistica_antes}
              resumen={datos.resumen}
            />
            <p className="text-xs text-muted-foreground">
              Limpieza versión {datos.version}
              {datos.fechaConfirmacion
                ? `, confirmada el ${new Date(datos.fechaConfirmacion).toLocaleDateString("es-MX")}`
                : ""}
              . Puedes pedir estas sugerencias en el chat: «¿qué análisis me sugieres para este
              instrumento?».
            </p>
          </>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
