import { ChevronDown } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { ColumnaEstadistica, EstadisticaLimpieza, FiabilidadBloque } from "@/types";
import { ETIQUETA_TIPO } from "../textos";
import { AYUDA, num, pct } from "./formato";
import { Barra, Cifra, Nivel, Subtitulo, TablaDesplazable, Td, Th } from "./piezas";

/** Medidas de una encuesta: fiabilidad, descriptivos, frecuencias y calidad de respuestas. */
export function EstadisticaEncuesta({ estadistica }: { estadistica: EstadisticaLimpieza }) {
  const columnas = estadistica.columnas ?? [];
  const bloques = Array.isArray(estadistica.fiabilidad) ? estadistica.fiabilidad : [];
  const numericas = columnas.filter((c) => c.numerico);
  const conFrecuencias = columnas.filter((c) => c.frecuencias && c.frecuencias.tabla.length > 0);
  const textos = columnas.filter((c) => c.texto);
  const encuestados = columnas[0] ? columnas[0].n + columnas[0].n_nulos : null;

  return (
    <div className="space-y-8">
      {estadistica.encuestados && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Cifra etiqueta="Encuestados analizados" valor={encuestados ?? "—"} />
          <Cifra
            etiqueta="Respondieron en línea recta"
            valor={estadistica.encuestados.linea_recta}
            ayuda="Eligieron la misma opción en todos los ítems de un bloque Likert."
          />
          <Cifra
            etiqueta="Encuestados incompletos"
            valor={estadistica.encuestados.incompletos}
            ayuda="Dejaron sin responder más de la mitad del instrumento."
          />
        </dl>
      )}

      <section className="space-y-3">
        <Subtitulo detalle="alfa de Cronbach">Fiabilidad</Subtitulo>
        {bloques.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Se necesita al menos un bloque de dos o más ítems Likert para calcular el alfa de
            Cronbach.
          </p>
        ) : (
          <div className="space-y-3">
            {bloques.map((b) => (
              <BloqueFiabilidad key={b.bloque} bloque={b} />
            ))}
          </div>
        )}
      </section>

      {numericas.length > 0 && (
        <section className="space-y-3">
          <Subtitulo detalle="escalas y respuestas numéricas">Estadística descriptiva</Subtitulo>
          <TablaDesplazable etiqueta="Estadística descriptiva por pregunta">
            <thead>
              <tr>
                <Th>Pregunta</Th>
                <Th>Tipo</Th>
                <Th alinear="derecha">n</Th>
                <Th alinear="derecha">Vacíos</Th>
                <Th alinear="derecha">Media</Th>
                <Th alinear="derecha">Mediana</Th>
                <Th alinear="derecha">Desv. est.</Th>
                <Th alinear="derecha">Mín – Máx</Th>
                <Th alinear="derecha">Q1 – Q3</Th>
                <Th alinear="derecha" titulo={AYUDA.asimetria}>
                  Asimetría
                </Th>
                <Th alinear="derecha" titulo={AYUDA.curtosis}>
                  Curtosis
                </Th>
                <Th alinear="derecha" titulo={AYUDA.atipicos}>
                  Atípicos σ / IQR
                </Th>
              </tr>
            </thead>
            <tbody>
              {numericas.map((c) => (
                <FilaDescriptiva key={c.id} columna={c} />
              ))}
            </tbody>
          </TablaDesplazable>
        </section>
      )}

      {conFrecuencias.length > 0 && (
        <section className="space-y-3">
          <Subtitulo detalle="opciones elegidas">Frecuencias</Subtitulo>
          <div className="grid gap-3 lg:grid-cols-2">
            {conFrecuencias.map((c) => (
              <TarjetaFrecuencias key={c.id} columna={c} />
            ))}
          </div>
        </section>
      )}

      {textos.length > 0 && (
        <section className="space-y-3">
          <Subtitulo detalle="respuestas abiertas">Texto libre</Subtitulo>
          <ul className="grid gap-2 sm:grid-cols-2">
            {textos.map((c) => (
              <li key={c.id} className="rounded-xl border border-border bg-card p-3 text-sm">
                <p className="line-clamp-2 font-semibold text-foreground" title={c.etiqueta}>
                  {c.etiqueta}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {c.n} respuestas · {c.texto?.respuestas_distintas} distintas ·{" "}
                  {num(c.texto?.palabras_promedio, 1)} palabras en promedio
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function BloqueFiabilidad({ bloque: b }: { bloque: FiabilidadBloque }) {
  return (
    <Collapsible className="rounded-2xl border border-border bg-card">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 p-4">
        <div className="min-w-[14rem] flex-1">
          <p className="font-semibold text-foreground">{b.bloque}</p>
          <p className="text-xs text-muted-foreground">
            {b.n_items} ítems · {b.n_casos} casos completos
            {b.invertidos.length > 0 && ` · ${b.invertidos.length} invertido(s) recodificado(s)`}
          </p>
        </div>
        <p className="flex items-center gap-2" title={AYUDA.alfa}>
          <span className="font-display text-2xl font-bold tabular-nums text-foreground">
            α = {num(b.alfa, 3)}
          </span>
          <Nivel nivel={b.interpretacion} />
        </p>
        {b.por_item.length > 0 && (
          <CollapsibleTrigger className="group inline-flex items-center gap-1 rounded-lg px-2 py-1 text-sm font-semibold text-primary hover:bg-primary-soft">
            Por ítem
            <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
          </CollapsibleTrigger>
        )}
      </div>
      {b.alfa === null && (
        <p className="px-4 pb-4 text-sm text-muted-foreground">
          No hay suficientes respuestas completas (o variación) para calcularlo.
        </p>
      )}
      <CollapsibleContent className="px-4 pb-4">
        <TablaDesplazable etiqueta={`Ítems del bloque ${b.bloque}`}>
          <thead>
            <tr>
              <Th>Ítem</Th>
              <Th alinear="derecha">Media</Th>
              <Th alinear="derecha" titulo={AYUDA.itemTotal}>
                r ítem-total
              </Th>
              <Th alinear="derecha" titulo={AYUDA.alfaSiSeElimina}>
                α si se elimina
              </Th>
            </tr>
          </thead>
          <tbody>
            {b.por_item.map((i) => {
              const resta =
                b.alfa !== null && i.alfa_si_se_elimina !== null && i.alfa_si_se_elimina > b.alfa;
              const debil = i.correlacion_item_total !== null && i.correlacion_item_total < 0.3;
              return (
                <tr key={i.item} className="border-t border-border/70">
                  <Td className="max-w-[20rem] whitespace-normal">
                    {i.item}
                    {b.invertidos.includes(i.item) && (
                      <span className="ml-2 text-xs text-muted-foreground">(invertido)</span>
                    )}
                  </Td>
                  <Td alinear="derecha">{num(i.media)}</Td>
                  <Td
                    alinear="derecha"
                    className={debil ? "font-bold text-accent-strong" : undefined}
                  >
                    {num(i.correlacion_item_total, 3)}
                  </Td>
                  <Td
                    alinear="derecha"
                    className={resta ? "font-bold text-accent-strong" : undefined}
                  >
                    {num(i.alfa_si_se_elimina, 3)}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </TablaDesplazable>
        <p className="mt-2 text-xs text-muted-foreground">
          En naranja: ítems que conviene revisar (poca relación con el bloque o que le restan
          consistencia).
        </p>
      </CollapsibleContent>
    </Collapsible>
  );
}

function FilaDescriptiva({ columna: c }: { columna: ColumnaEstadistica }) {
  const d = c.numerico;
  if (!d) return null;
  return (
    <tr className="border-t border-border/70">
      <Td className="max-w-[18rem]">
        <span className="line-clamp-2" title={c.etiqueta}>
          {c.etiqueta}
        </span>
      </Td>
      <Td className="whitespace-nowrap text-muted-foreground">{ETIQUETA_TIPO[c.tipo] ?? c.tipo}</Td>
      <Td alinear="derecha">{d.n}</Td>
      <Td alinear="derecha">{pct(c.pct_nulos)}</Td>
      <Td alinear="derecha" className="font-semibold">
        {num(d.media)}
      </Td>
      <Td alinear="derecha">{num(d.mediana)}</Td>
      <Td alinear="derecha">{num(d.desviacion)}</Td>
      <Td alinear="derecha">
        {num(d.min)} – {num(d.max)}
      </Td>
      <Td alinear="derecha">
        {num(d.q1)} – {num(d.q3)}
      </Td>
      <Td alinear="derecha">{num(d.asimetria)}</Td>
      <Td alinear="derecha">{num(d.curtosis)}</Td>
      <Td alinear="derecha">
        {c.atipicos ? (
          <span
            className={
              c.atipicos.sigma + c.atipicos.iqr > 0 ? "font-bold text-accent-strong" : undefined
            }
          >
            {c.atipicos.sigma} / {c.atipicos.iqr}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </Td>
    </tr>
  );
}

function TarjetaFrecuencias({ columna: c }: { columna: ColumnaEstadistica }) {
  const f = c.frecuencias!;
  const moda = Array.isArray(f.moda) ? f.moda.join(", ") : f.moda;
  const total = f.tabla.reduce((s, r) => s + r.n, 0);
  return (
    <article className="space-y-3 rounded-2xl border border-border bg-card p-4">
      <header className="space-y-0.5">
        <h5 className="line-clamp-2 text-sm font-semibold text-foreground" title={c.etiqueta}>
          {c.etiqueta}
        </h5>
        <p className="text-xs text-muted-foreground">
          {ETIQUETA_TIPO[c.tipo] ?? c.tipo} · {total} respuestas
          {moda && ` · moda: ${moda}`}
          {c.n_excluidos ? ` · ${c.n_excluidos} «No sé / No aplica» excluidas` : ""}
        </p>
      </header>
      <ul className="space-y-1.5">
        {f.tabla.slice(0, 10).map((r) => (
          <Barra
            key={r.valor}
            etiqueta={r.valor}
            n={r.n}
            proporcion={r.pct}
            destacada={moda === r.valor}
          />
        ))}
      </ul>
      {(f.otras > 0 || f.tabla.length > 10) && (
        <p className="text-xs text-muted-foreground">
          y {f.otras + Math.max(0, f.tabla.length - 10)} opción(es) más
        </p>
      )}
    </article>
  );
}
