import { cn } from "@/lib/utils";
import type { EstadisticaLimpieza } from "@/types";
import { AYUDA, num, pct } from "./formato";
import { Cifra, Subtitulo, TablaDesplazable, Td, Th } from "./piezas";

/** Qué respondieron los alumnos en cada reactivo. Las pruebas no se califican: no hay respuesta correcta. */
export function EstadisticaPrueba({ estadistica }: { estadistica: EstadisticaLimpieza }) {
  const respuestas = estadistica.respuestas;
  const resumen = estadistica.resumen_reactivos;
  const reactivos = estadistica.reactivos ?? [];

  return (
    <div className="space-y-8">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cifra etiqueta="Alumnos" valor={num(respuestas?.n_alumnos, 0)}>
          <span className="text-xs text-muted-foreground">
            {respuestas?.n_reactivos ?? 0} reactivos
          </span>
        </Cifra>
        <Cifra
          etiqueta="Sin respuesta válida"
          valor={pct(respuestas?.pct_sin_respuesta)}
          ayuda={AYUDA.sinRespuesta}
        >
          <span className="text-xs text-muted-foreground">nulas y no respondidas</span>
        </Cifra>
        {resumen && (
          <>
            <Cifra etiqueta="Reactivos con mucha no respuesta" valor={resumen.mucha_no_respuesta}>
              <span className="text-xs text-muted-foreground">
                más del 20 % sin respuesta válida
              </span>
            </Cifra>
            <Cifra
              etiqueta="Reactivos casi unánimes"
              valor={resumen.casi_unanimes}
              ayuda={AYUDA.casiUnanime}
            >
              <span className="text-xs text-muted-foreground">
                {resumen.con_opciones_sin_elegir} con opciones que nadie eligió
              </span>
            </Cifra>
          </>
        )}
      </dl>

      <section className="space-y-3">
        <Subtitulo detalle="la prueba no se califica: se describe lo que eligieron los alumnos">
          Respuestas por reactivo
        </Subtitulo>
        <TablaDesplazable etiqueta="Respuestas por reactivo">
          <thead>
            <tr>
              <Th>Reactivo</Th>
              <Th titulo={AYUDA.opcionMasElegida}>Opción más elegida</Th>
              <Th alinear="derecha" titulo={AYUDA.sinRespuesta}>
                Sin respuesta
              </Th>
              <Th>Opciones elegidas</Th>
            </tr>
          </thead>
          <tbody>
            {reactivos.map((r) => (
              <tr key={r.pregunta} className="border-t border-border/70">
                <Td className="font-semibold">{r.pregunta}</Td>
                <Td>
                  {r.opcion_mas_elegida ? (
                    <span className="font-mono">
                      {r.opcion_mas_elegida.opcion}{" "}
                      <span className="text-muted-foreground">
                        ({pct(r.opcion_mas_elegida.pct)})
                      </span>
                    </span>
                  ) : (
                    "—"
                  )}
                  {r.descriptivos?.media != null && (
                    <span className="block text-xs text-muted-foreground">
                      media {num(r.descriptivos.media)}
                    </span>
                  )}
                </Td>
                <Td alinear="derecha">
                  <span className={cn(r.mucha_no_respuesta && "font-semibold text-accent-strong")}>
                    {pct(r.pct_sin_respuesta)}
                  </span>
                </Td>
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
                            r.opcion_mas_elegida?.opcion === d.opcion
                              ? "bg-primary/10 font-bold text-primary"
                              : r.opciones_sin_elegir.includes(d.opcion)
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
          Resaltada, la opción más elegida (no significa que sea la correcta: Indagata no califica
          las pruebas); en naranja, las opciones que ningún alumno eligió.
        </p>
      </section>
    </div>
  );
}
