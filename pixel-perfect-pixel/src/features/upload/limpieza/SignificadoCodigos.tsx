import { useMemo, useState } from "react";
import { BookOpenText, ChevronDown, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { CodigosLimpieza, ColumnaCodigos, SignificadoCodigos as Significado } from "@/types";

interface SignificadoCodigosProps {
  codigos: CodigosLimpieza;
  /** Cambio de una columna (el paso lo guarda poco después, junto con los demás). */
  onCambiar: (clave: string, significado: Significado) => void;
}

/** Firma del conjunto de códigos de una columna, para encontrar las que comparten escala («1–5»). */
function firma(c: ColumnaCodigos): string {
  return c.codigos.map((x) => x.codigo).join("|");
}

/**
 * Microdatos: texto de cada pregunta en código y significado de cada código. Viene precargado con el
 * diccionario de datos (si se subió) y es opcional: sin significado, la pregunta conserva su encabezado
 * y la respuesta su código.
 */
export function SignificadoCodigos({ codigos, onCambiar }: SignificadoCodigosProps) {
  const { columnas, diccionario } = codigos;
  const [borrador, setBorrador] = useState<Record<string, Significado>>(() =>
    Object.fromEntries(
      columnas.map((c) => [c.clave, { pregunta: c.pregunta, valores: c.etiquetas }]),
    ),
  );
  // Abierto de entrada si hay encabezados en código que aún no tienen texto.
  const [abierto, setAbierto] = useState(() =>
    columnas.some((c) => c.encabezado_codigo && !c.pregunta),
  );
  const porFirma = useMemo(() => {
    const mapa = new Map<string, string[]>();
    for (const c of columnas) {
      if (c.codigos.length) mapa.set(firma(c), [...(mapa.get(firma(c)) ?? []), c.clave]);
    }
    return mapa;
  }, [columnas]);
  const conTexto = columnas.filter((c) => borrador[c.clave]?.pregunta).length;

  function cambiar(clave: string, significado: Significado) {
    setBorrador((b) => ({ ...b, [clave]: significado }));
    onCambiar(clave, significado);
  }

  function copiarEtiquetas(origen: ColumnaCodigos) {
    const valores = borrador[origen.clave]?.valores ?? {};
    for (const clave of porFirma.get(firma(origen)) ?? []) {
      if (clave === origen.clave) continue;
      cambiar(clave, { pregunta: borrador[clave]?.pregunta ?? null, valores: { ...valores } });
    }
  }

  return (
    <section className="space-y-3 rounded-2xl border border-border bg-card p-5">
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 text-left"
        aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
      >
        <span className="flex gap-3">
          <BookOpenText className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
          <span>
            <span className="block font-display text-lg font-bold text-foreground">
              Significado de los códigos
              <span className="ml-2 text-sm font-semibold text-muted-foreground">
                {conTexto} de {columnas.length} con texto
              </span>
            </span>
            <span className="block text-sm text-muted-foreground">
              Tu archivo tiene columnas con códigos (P1, P2… o respuestas como 1, 2, A). Escribe qué
              pregunta es cada una y qué significa cada código: así el chat responde «Mujer» y no
              «2». Es opcional.
            </span>
          </span>
        </span>
        <ChevronDown
          className={cn("mt-1 size-5 shrink-0 transition-transform", abierto && "rotate-180")}
          aria-hidden
        />
      </button>

      {diccionario && (
        <p className="rounded-xl bg-muted/40 p-3 text-sm text-foreground">
          Se precargó con el diccionario de datos <strong>{diccionario.nombre}</strong>:{" "}
          {diccionario.emparejadas} columna{diccionario.emparejadas === 1 ? "" : "s"}.
          {diccionario.n_sin_columna > 0 && (
            <>
              {" "}
              {diccionario.n_sin_columna} variable{diccionario.n_sin_columna === 1 ? "" : "s"} del
              diccionario no está{diccionario.n_sin_columna === 1 ? "" : "n"} en el archivo:{" "}
              {diccionario.sin_columna.join(", ")}
              {diccionario.n_sin_columna > diccionario.sin_columna.length ? "…" : ""}.
            </>
          )}
        </p>
      )}

      {abierto && (
        <ul className="divide-y divide-border">
          {columnas.map((c) => {
            const actual = borrador[c.clave] ?? { pregunta: null, valores: {} };
            const iguales = (porFirma.get(firma(c))?.length ?? 1) - 1;
            return (
              <li key={c.clave} className="space-y-3 py-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-mono text-sm font-semibold text-foreground">{c.etiqueta}</p>
                  {c.origen && (
                    <span className="text-xs text-muted-foreground">
                      {c.origen === "diccionario"
                        ? "del diccionario"
                        : c.origen === "anterior"
                          ? "de la versión anterior"
                          : "escrito por ti"}
                    </span>
                  )}
                </div>
                <Input
                  className="h-10 text-sm"
                  aria-label={`Texto de la pregunta ${c.etiqueta}`}
                  placeholder="Texto de la pregunta (p. ej. ¿Cuál es tu sexo?)"
                  value={actual.pregunta ?? ""}
                  onChange={(e) =>
                    cambiar(c.clave, { ...actual, pregunta: e.target.value || null })
                  }
                />
                {c.codigos.length > 0 && (
                  <div className="space-y-2">
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                      {c.codigos.map(({ codigo, n }) => (
                        <label key={codigo} className="flex items-center gap-2 text-sm">
                          <span className="w-10 shrink-0 text-right font-mono font-semibold text-foreground">
                            {codigo}
                          </span>
                          <span className="text-muted-foreground">=</span>
                          <Input
                            className="h-9 text-sm"
                            placeholder={
                              n != null ? `${n} respuesta${n === 1 ? "" : "s"}` : "Significado"
                            }
                            value={actual.valores[codigo] ?? ""}
                            onChange={(e) => {
                              const valores = { ...actual.valores };
                              if (e.target.value) valores[codigo] = e.target.value;
                              else delete valores[codigo];
                              cambiar(c.clave, { ...actual, valores });
                            }}
                          />
                        </label>
                      ))}
                    </div>
                    {iguales > 0 && Object.keys(actual.valores).length > 0 && (
                      <Button variant="ghost" size="sm" onClick={() => copiarEtiquetas(c)}>
                        <Copy /> Usar estos significados en {iguales} columna
                        {iguales === 1 ? "" : "s"} con los mismos códigos
                      </Button>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
