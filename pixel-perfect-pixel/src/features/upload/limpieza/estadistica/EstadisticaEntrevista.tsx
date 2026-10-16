import type { EstadisticaLimpieza } from "@/types";
import { etiquetaOpcion } from "../textos";
import { num, pct } from "./formato";
import { Barra, Cifra, Subtitulo, TablaDesplazable, Td, Th } from "./piezas";

/**
 * Estadística de una entrevista centrada en las RESPUESTAS de los entrevistados:
 * cuántos respondieron cada pregunta y qué tan extensas son sus respuestas. El
 * entrevistador solo pregunta, así que su participación aparece aparte, por rol.
 */
export function EstadisticaEntrevista({ estadistica }: { estadistica: EstadisticaLimpieza }) {
  const preguntas = estadistica.preguntas;
  if (!preguntas) return <EstadisticaHablantes estadistica={estadistica} />;

  const entrevistados = estadistica.n_participantes ?? 0;
  const respuestas = estadistica.palabras_por_respuesta;
  const participantes = estadistica.participantes ?? [];
  const roles = estadistica.palabras_por_rol ?? [];

  return (
    <div className="space-y-8">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Cifra etiqueta="Entrevistados" valor={entrevistados} />
        <Cifra etiqueta="Preguntas del entrevistador" valor={estadistica.n_preguntas ?? 0} />
        <Cifra etiqueta="Respuestas" valor={estadistica.n_respuestas ?? 0} />
        <Cifra etiqueta="Palabras por respuesta (media)" valor={num(respuestas?.media, 1)}>
          {respuestas?.mediana != null && (
            <span className="text-xs text-muted-foreground">
              mediana {num(respuestas.mediana, 1)}
            </span>
          )}
        </Cifra>
      </dl>

      {preguntas.length > 0 ? (
        <section className="space-y-3">
          <Subtitulo>Respuestas por pregunta</Subtitulo>
          {entrevistados > 0 && (
            <ul className="space-y-1.5 rounded-2xl border border-border bg-card p-4">
              {preguntas.map((p) => (
                <Barra
                  key={p.pregunta}
                  etiqueta={`${p.pregunta}. ${p.texto}`}
                  n={p.n_respuestas}
                  proporcion={p.n_respuestas / entrevistados}
                  destacada={p.sin_respuesta === 0}
                />
              ))}
            </ul>
          )}
          <TablaDesplazable etiqueta="Respuestas por pregunta">
            <thead>
              <tr>
                <Th>Pregunta</Th>
                <Th alinear="derecha">Respondieron</Th>
                <Th alinear="derecha">Sin respuesta</Th>
                <Th alinear="derecha">Palabras (media)</Th>
                <Th alinear="derecha">Mín.</Th>
                <Th alinear="derecha">Máx.</Th>
              </tr>
            </thead>
            <tbody>
              {preguntas.map((p) => (
                <tr key={p.pregunta} className="border-t border-border/70">
                  <Td className="max-w-[26rem] whitespace-normal">
                    <span className="font-semibold">{p.pregunta}.</span> {p.texto}
                  </Td>
                  <Td alinear="derecha">{p.n_respuestas}</Td>
                  <Td
                    alinear="derecha"
                    className={p.sin_respuesta > 0 ? "font-semibold text-accent-strong" : ""}
                  >
                    {p.sin_respuesta}
                  </Td>
                  <Td alinear="derecha">{num(p.palabras.media, 1)}</Td>
                  <Td alinear="derecha">{num(p.palabras.min, 0)}</Td>
                  <Td alinear="derecha">{num(p.palabras.max, 0)}</Td>
                </tr>
              ))}
            </tbody>
          </TablaDesplazable>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">
          No se identificaron preguntas del entrevistador: revisa los roles.
        </p>
      )}

      {participantes.length > 0 && (
        <details className="space-y-3 rounded-2xl border border-border bg-card p-4">
          <summary className="cursor-pointer font-display text-sm font-bold text-foreground">
            Por entrevistado ({participantes.length})
          </summary>
          <div className="mt-3">
            <TablaDesplazable etiqueta="Respuestas por entrevistado">
              <thead>
                <tr>
                  <Th>Entrevistado</Th>
                  <Th alinear="derecha">Preguntas respondidas</Th>
                  <Th alinear="derecha">Palabras</Th>
                  <Th alinear="derecha">Palabras por respuesta</Th>
                </tr>
              </thead>
              <tbody>
                {participantes.map((p) => (
                  <tr key={p.id} className="border-t border-border/70">
                    <Td className="font-semibold">{p.id}</Td>
                    <Td alinear="derecha">
                      {p.respuestas} de {estadistica.n_preguntas ?? 0}
                    </Td>
                    <Td alinear="derecha">{p.palabras}</Td>
                    <Td alinear="derecha">{num(p.palabras_por_respuesta, 1)}</Td>
                  </tr>
                ))}
              </tbody>
            </TablaDesplazable>
          </div>
        </details>
      )}

      {roles.length > 0 && (
        <section className="space-y-3">
          <Subtitulo>Palabras por rol</Subtitulo>
          <p className="text-sm text-muted-foreground">
            El entrevistador solo formula las preguntas; lo esperado es que la mayor parte del texto
            sean respuestas.
          </p>
          <ul className="space-y-1.5 rounded-2xl border border-border bg-card p-4">
            {roles.map((r) => (
              <Barra
                key={r.rol}
                etiqueta={r.rol === "sin_rol" ? "Sin rol" : etiquetaOpcion(r.rol)}
                n={r.palabras}
                proporcion={r.pct_palabras}
                destacada={r.rol === "entrevistado"}
              />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/** Reportes anteriores (sin medidas por pregunta): participación por hablante. */
function EstadisticaHablantes({ estadistica }: { estadistica: EstadisticaLimpieza }) {
  const hablantes = estadistica.hablantes ?? [];
  const turnos = estadistica.palabras_por_turno;

  return (
    <div className="space-y-8">
      {turnos && (
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Cifra etiqueta="Palabras por turno (media)" valor={num(turnos.media, 1)} />
          <Cifra etiqueta="Mediana" valor={num(turnos.mediana, 1)} />
          <Cifra etiqueta="Desviación estándar" valor={num(turnos.desviacion, 1)} />
          <Cifra etiqueta="Turno más largo" valor={num(turnos.max, 0)}>
            <span className="text-xs text-muted-foreground">palabras</span>
          </Cifra>
        </dl>
      )}

      {hablantes.length > 0 ? (
        <section className="space-y-3">
          <Subtitulo>Participación por hablante</Subtitulo>
          <TablaDesplazable etiqueta="Participación por hablante">
            <thead>
              <tr>
                <Th>Hablante</Th>
                <Th>Rol</Th>
                <Th alinear="derecha">Turnos</Th>
                <Th alinear="derecha">Palabras</Th>
                <Th alinear="derecha">% de las palabras</Th>
              </tr>
            </thead>
            <tbody>
              {hablantes.map((h) => (
                <tr key={h.nombre} className="border-t border-border/70">
                  <Td className="font-semibold">{h.nombre}</Td>
                  <Td className="text-muted-foreground">{h.rol ? etiquetaOpcion(h.rol) : "—"}</Td>
                  <Td alinear="derecha">{h.turnos}</Td>
                  <Td alinear="derecha">{h.palabras}</Td>
                  <Td alinear="derecha">{pct(h.pct_palabras)}</Td>
                </tr>
              ))}
            </tbody>
          </TablaDesplazable>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">
          No se reconocieron hablantes: la entrevista se dividió por párrafos.
        </p>
      )}
    </div>
  );
}
