import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { analizarRespuestas, corregirAnalisis, getAnalisisRespuestas } from "@/api/conocimiento";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type {
  AnalisisEntrevista,
  FuncionUnidad,
  IntercambioAnalizado,
  MarcoTemporal,
  UnidadRespuesta,
} from "@/types";

const POR_PAGINA = 8;
const ESPERA_MS = 3000;

const FUNCION: Record<FuncionUnidad, string> = {
  responde: "Responde",
  contexto: "Contexto",
  digresion: "Digresión",
};
const MARCO: Record<MarcoTemporal, string> = {
  actual: "presente",
  pasado: "pasado",
  hipotetico: "supuesto",
  general: "general",
};
const POSTURAS: Record<string, string> = {
  si: "Sí",
  no: "No",
  ambivalente: "Ambivalente",
  no_aplica: "No aplica",
  sin_determinar: "Sin determinar",
};

function corto(id: string): string {
  return id.split("-").pop() ?? id;
}

interface FilaProps {
  idCrudo: number;
  item: IntercambioAnalizado;
  onGuardado: (item: IntercambioAnalizado) => void;
}

/** Una respuesta: sus unidades (editables) y la postura global. */
function FilaIntercambio({ idCrudo, item, onGuardado }: FilaProps) {
  const an = item.analisis;
  const [unidades, setUnidades] = useState<UnidadRespuesta[]>(an?.unidades ?? []);
  const [postura, setPostura] = useState<string>(an?.postura ?? "sin_determinar");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!an) return null;

  const cambiarFuncion = (i: number, funcion: FuncionUnidad) =>
    setUnidades((us) => us.map((u, k) => (k === i ? { ...u, funcion } : u)));

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      const r = await corregirAnalisis(idCrudo, item.participante, item.n, { unidades, postura });
      onGuardado({ ...item, analisis: r.analisis });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar la corrección.");
    } finally {
      setGuardando(false);
    }
  };

  return (
    <li className="space-y-3 rounded-xl border border-border bg-card p-4">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-0.5">
          <p className="text-xs font-semibold text-muted-foreground">
            {corto(item.participante)}
            {item.pregunta_id ? ` · ${corto(item.pregunta_id)}` : ""}
            {an.metodo === "reglas" ? " · análisis por reglas" : ""}
          </p>
          <p className="text-sm font-medium text-foreground">{item.pregunta}</p>
        </div>
        {an.estado === "revisado" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-primary-soft px-2 py-0.5 text-xs font-semibold text-primary">
            <CheckCircle2 className="size-3.5" aria-hidden /> Revisado
          </span>
        )}
      </header>

      <ul className="space-y-2" aria-label="Unidades de la respuesta">
        {unidades.map((u, i) => (
          <li
            key={`${i}-${u.texto}`}
            className={cn(
              "flex flex-col gap-2 rounded-lg border-l-4 bg-muted/40 p-2.5 sm:flex-row sm:items-start",
              u.funcion === "responde" ? "border-primary" : "border-border",
            )}
          >
            <p
              className={cn(
                "flex-1 text-sm leading-relaxed",
                u.funcion === "responde" ? "text-foreground" : "text-muted-foreground",
              )}
            >
              «{u.texto}»
              <span className="ml-1 text-xs text-muted-foreground">
                ({MARCO[u.marco_temporal]})
              </span>
            </p>
            <Select value={u.funcion} onValueChange={(v) => cambiarFuncion(i, v as FuncionUnidad)}>
              <SelectTrigger
                className="h-8 w-full text-xs sm:w-36"
                aria-label="Función de la unidad"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(FUNCION).map(([valor, etiqueta]) => (
                  <SelectItem key={valor} value={valor} className="text-xs">
                    {etiqueta}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </li>
        ))}
      </ul>

      <footer className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          Postura
          <Select value={postura} onValueChange={setPostura}>
            <SelectTrigger className="h-8 w-40 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(POSTURAS).map(([valor, etiqueta]) => (
                <SelectItem key={valor} value={valor} className="text-xs">
                  {etiqueta}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        {an.motivo && (
          <p className="text-xs text-muted-foreground">
            Motivo: <span className="text-foreground">«{an.motivo}»</span>
          </p>
        )}
        <Button
          size="sm"
          variant="outline"
          className="ml-auto"
          onClick={guardar}
          disabled={guardando}
        >
          {guardando ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
          Marcar como revisado
        </Button>
        {error && <p className="w-full text-xs text-destructive">{error}</p>}
      </footer>
    </li>
  );
}

/**
 * Análisis de respuestas de entrevista: divide cada respuesta en unidades literales
 * (qué responde a la pregunta, qué es contexto de otro momento y qué es digresión),
 * con la postura y el motivo. El investigador revisa y corrige antes de guardar.
 */
export function AnalisisRespuestas({ idCrudo }: { idCrudo: number }) {
  const [datos, setDatos] = useState<AnalisisEntrevista | null>(null);
  const [visibles, setVisibles] = useState(POR_PAGINA);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      setDatos(await getAnalisisRespuestas(idCrudo));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo leer el análisis.");
    }
  }, [idCrudo]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  useEffect(() => {
    if (datos?.estado !== "en_curso") return;
    const t = window.setTimeout(() => void cargar(), ESPERA_MS);
    return () => window.clearTimeout(t);
  }, [datos, cargar]);

  const iniciar = async () => {
    setError(null);
    try {
      await analizarRespuestas(idCrudo);
      await cargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar el análisis.");
    }
  };

  const actualizar = (item: IntercambioAnalizado) =>
    setDatos(
      (d) =>
        d && {
          ...d,
          revisados: d.revisados + (item.analisis?.estado === "revisado" ? 1 : 0),
          intercambios: d.intercambios.map((x) =>
            x.participante === item.participante && x.n === item.n ? item : x,
          ),
        },
    );

  const analizados = (datos?.intercambios ?? []).filter((x) => x.analisis);
  const enCurso = datos?.estado === "en_curso";

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-card p-4 shadow-card sm:p-5">
      <header className="space-y-1">
        <h3 className="font-display text-base font-bold text-foreground">
          Análisis de las respuestas
        </h3>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Separamos en cada respuesta lo que contesta a la pregunta de lo que es contexto (por
          ejemplo, un relato de otro momento) o digresión, con la postura y el motivo. Cada
          fragmento se copia tal cual de la respuesta. Revísalo antes de guardar: el chat usará lo
          que marques como «Responde».
        </p>
      </header>

      {datos && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Button size="sm" onClick={iniciar} disabled={enCurso}>
            {enCurso ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Sparkles className="size-4" aria-hidden />
            )}
            {analizados.length ? "Volver a analizar las no revisadas" : "Analizar respuestas"}
          </Button>
          {enCurso && (
            <span className="text-muted-foreground">
              Analizando {datos.hechos} de {datos.total}…
            </span>
          )}
          {analizados.length > 0 && !enCurso && (
            <span className="text-muted-foreground">
              {analizados.length} respuestas analizadas · {datos.revisados} revisadas
            </span>
          )}
        </div>
      )}
      {(error || datos?.estado === "error") && (
        <p className="text-sm text-destructive">{error ?? datos?.mensaje}</p>
      )}

      {analizados.length > 0 && (
        <>
          <ul className="space-y-3">
            {analizados.slice(0, visibles).map((item) => (
              <FilaIntercambio
                key={`${item.participante}-${item.n}-${item.analisis?.estado}`}
                idCrudo={idCrudo}
                item={item}
                onGuardado={actualizar}
              />
            ))}
          </ul>
          {visibles < analizados.length && (
            <Button variant="ghost" size="sm" onClick={() => setVisibles((v) => v + POR_PAGINA)}>
              Ver {Math.min(POR_PAGINA, analizados.length - visibles)} más de{" "}
              {analizados.length - visibles}
            </Button>
          )}
        </>
      )}
    </section>
  );
}
