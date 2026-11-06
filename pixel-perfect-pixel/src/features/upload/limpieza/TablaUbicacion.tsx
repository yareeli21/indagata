/** Una celda de un hallazgo o de una transformación: dónde está y qué valor tenía. */
export interface CeldaUbicacion {
  fila: number;
  columna?: string;
  valor?: string | null;
  antes?: string;
  despues?: string;
  /** Hallazgos por fila: las respuestas de esa fila en las columnas que importan. */
  valores?: Record<string, string | null>;
}

/** Valor tal cual, con los espacios visibles («␣») para que se note qué se quitó. */
function visible(valor: string | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "(vacío)";
  return valor.replace(/^ +| +$/g, (m) => "␣".repeat(m.length));
}

/** Lista de los lugares exactos donde la limpieza encontró o cambió algo (fila desde 1, sin el encabezado). */
export function TablaUbicacion({
  celdas,
  total,
}: {
  celdas: CeldaUbicacion[];
  total?: number | undefined;
}) {
  if (celdas.length === 0) return null;
  const porFila = celdas.some((c) => c.valores);
  const cambio = celdas.some((c) => c.antes !== undefined);
  const columnasFila = porFila ? Object.keys(celdas[0]?.valores ?? {}) : [];
  return (
    <div className="space-y-1">
      <div className="max-h-72 overflow-auto rounded-xl border border-border">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-muted text-left text-muted-foreground">
            <tr>
              <th className="px-2 py-1.5 font-semibold">Fila</th>
              {porFila ? (
                columnasFila.map((c) => (
                  <th key={c} className="max-w-40 truncate px-2 py-1.5 font-semibold" title={c}>
                    {c}
                  </th>
                ))
              ) : (
                <>
                  <th className="px-2 py-1.5 font-semibold">Pregunta</th>
                  {cambio ? (
                    <>
                      <th className="px-2 py-1.5 font-semibold">Antes</th>
                      <th className="px-2 py-1.5 font-semibold">Después</th>
                    </>
                  ) : (
                    <th className="px-2 py-1.5 font-semibold">Valor</th>
                  )}
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {celdas.map((c, i) => (
              <tr key={`${c.fila}-${c.columna ?? ""}-${i}`} className="border-t border-border/60">
                <td className="px-2 py-1 font-semibold tabular-nums">{c.fila}</td>
                {porFila ? (
                  columnasFila.map((col) => (
                    <td
                      key={col}
                      className="max-w-40 truncate px-2 py-1"
                      title={c.valores?.[col] ?? ""}
                    >
                      {visible(c.valores?.[col])}
                    </td>
                  ))
                ) : (
                  <>
                    <td className="max-w-56 truncate px-2 py-1" title={c.columna}>
                      {c.columna}
                    </td>
                    {cambio ? (
                      <>
                        <td className="px-2 py-1 font-mono text-accent-strong">
                          {visible(c.antes)}
                        </td>
                        <td className="px-2 py-1 font-mono">{visible(c.despues)}</td>
                      </>
                    ) : (
                      <td className="px-2 py-1 font-mono">{visible(c.valor)}</td>
                    )}
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        La fila se cuenta desde 1, sin el encabezado; «␣» marca un espacio.
        {total !== undefined &&
          total > celdas.length &&
          ` Se muestran ${celdas.length} de ${total}.`}
      </p>
    </div>
  );
}
