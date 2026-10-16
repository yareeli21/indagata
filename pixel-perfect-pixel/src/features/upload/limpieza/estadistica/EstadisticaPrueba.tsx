import { cn } from "@/lib/utils";
import type { EstadisticaLimpieza } from "@/types";
import { AYUDA, num, pct } from "./formato";
import { Cifra, Nivel, Subtitulo, TablaDesplazable, Td, Th } from "./piezas";

/** Análisis de reactivos de una prueba: dificultad, discriminación, distractores y KR-20. */
export function EstadisticaPrueba({ estadistica }: { estadistica: EstadisticaLimpieza }) {
  const fiabilidad =
    estadistica.fiabilidad && !Array.isArray(estadistica.fiabilidad)
      ? estadistica.fiabilidad
      : null;
  const puntajes = estadistica.puntajes;
  const resumen = estadistica.resumen_reactivos;
  const reactivos = estadistica.reactivos ?? [];

  return (
    <div className="space-y-8">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cifra etiqueta="Fiabilidad KR-20" valor={num(fiabilidad?.kr20, 3)} ayuda={AYUDA.kr20}>
          <Nivel nivel={fiabilidad?.interpretacion} />
        </Cifra>
        <Cifra
          etiqueta="Puntaje promedio"
          valor={
            <>
              {num(puntajes?.media)}
              <span className="text-base text-muted-foreground"> / {puntajes?.maximo_posible}</span>
            </>
          }
        >
          <span className="text-xs text-muted-foreground">
            mediana {num(puntajes?.mediana)} · desv. est. {num(puntajes?.desviacion)}
          </span>
        </Cifra>
        <Cifra etiqueta="Rango de puntajes" valor={`${num(puntajes?.min)} – ${num(puntajes?.max)}`}>
          <span className="text-xs text-muted-foreground">
            {fiabilidad?.n_alumnos ?? 0} alumnos analizados
          </span>
        </Cifra>
        {resumen && (
          <Cifra
            etiqueta="Reactivos por dificultad"
            valor={`${resumen.faciles} · ${resumen.medios} · ${resumen.dificiles}`}
          >
            <span className="text-xs text-muted-foreground">
              fáciles · medios · difíciles
              {resumen.discriminacion_pobre > 0 &&
                ` · ${resumen.discriminacion_pobre} discriminan poco`}
            </span>
          </Cifra>
        )}
      </dl>

      <section className="space-y-3">
        <Subtitulo detalle="las nulas y no respondidas cuentan como incorrectas">
          Análisis de reactivos
        </Subtitulo>
        <TablaDesplazable etiqueta="Análisis de reactivos">
          <thead>
            <tr>
              <Th>Reactivo</Th>
              <Th>Clave</Th>
              <Th alinear="derecha" titulo={AYUDA.dificultad}>
                Dificultad p
              </Th>
              <Th alinear="derecha" titulo={AYUDA.discriminacion}>
                Discriminación D
              </Th>
              <Th alinear="derecha" titulo={AYUDA.puntoBiserial}>
                r punto-biserial
              </Th>
              <Th>Opciones elegidas</Th>
            </tr>
          </thead>
          <tbody>
            {reactivos.map((r) => (
              <tr key={r.pregunta} className="border-t border-border/70">
                <Td className="font-semibold">{r.pregunta}</Td>
                <Td className="font-mono">{r.respuesta_correcta}</Td>
                <Td alinear="derecha">
                  <span className="inline-flex items-center gap-2">
                    {num(r.dificultad)} <Nivel nivel={r.nivel_dificultad} />
                  </span>
                </Td>
                <Td alinear="derecha">
                  <span className="inline-flex items-center gap-2">
                    {num(r.discriminacion)} <Nivel nivel={r.nivel_discriminacion} />
                  </span>
                </Td>
                <Td alinear="derecha">{num(r.correlacion_punto_biserial, 3)}</Td>
                <Td>
                  <ul
                    className="flex flex-wrap gap-1.5"
                    aria-label={`Opciones elegidas en ${r.pregunta}`}
                  >
                    {r.distribucion
                      .filter((d) => d.n > 0 || !["nula", "NR"].includes(d.opcion))
                      .map((d) => (
                        <li
                          key={d.opcion}
                          title={`${d.n} alumno(s) · ${pct(d.pct)}`}
                          className={cn(
                            "rounded-md px-1.5 py-0.5 text-xs tabular-nums",
                            d.correcta
                              ? "bg-success-soft font-bold text-success"
                              : r.distractores_sin_elegir.includes(d.opcion)
                                ? "bg-accent-soft text-accent-strong"
                                : "bg-muted text-foreground",
                          )}
                        >
                          {d.opcion === "nula" ? "Nula" : d.opcion} {d.n}
                        </li>
                      ))}
                  </ul>
                </Td>
              </tr>
            ))}
          </tbody>
        </TablaDesplazable>
        <p className="text-xs text-muted-foreground">
          En verde, la respuesta correcta; en naranja, distractores que nadie eligió (no funcionan
          como opción plausible).
        </p>
      </section>
    </div>
  );
}
