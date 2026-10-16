import { ArrowRight, Info, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { VistaFinalLimpieza as Vista } from "@/types";
import { ComparacionAntesDespues } from "./estadistica/ComparacionAntesDespues";
import { EstadisticaLimpieza } from "./estadistica/EstadisticaLimpieza";

interface VistaFinalLimpiezaProps {
  vista: Vista;
  reajustando: boolean;
  onReajustar: () => void;
  onContinuar: () => void;
}

/** Resultado de la limpieza: cifras clave, una muestra del instrumento limpio, las medidas
 * estadísticas (antes y después) y el siguiente paso. */
export function VistaFinalLimpieza({
  vista,
  reajustando,
  onReajustar,
  onContinuar,
}: VistaFinalLimpiezaProps) {
  return (
    <div className="space-y-6">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {vista.cifras.map((c) => (
          <div
            key={c.etiqueta}
            className="flex flex-col-reverse rounded-2xl border border-border bg-card p-4 shadow-card"
          >
            <dt className="text-sm text-muted-foreground">{c.etiqueta}</dt>
            <dd className="font-display text-3xl font-bold tabular-nums text-primary">{c.valor}</dd>
          </div>
        ))}
      </dl>

      {/* Limpiezas confirmadas antes de las medidas estadísticas solo traen la vista previa. */}
      {vista.comparacion?.length || vista.estadistica ? (
        <Tabs defaultValue="vista">
          <TabsList className="h-auto flex-wrap">
            <TabsTrigger value="vista">Vista previa</TabsTrigger>
            <TabsTrigger value="estadistica">Estadística</TabsTrigger>
            {vista.comparacion?.length ? (
              <TabsTrigger value="comparacion">Antes y después</TabsTrigger>
            ) : null}
          </TabsList>
          <TabsContent value="vista" className="mt-4">
            <VistaPrevia vista={vista} />
          </TabsContent>
          <TabsContent value="estadistica" className="mt-4">
            <EstadisticaLimpieza
              despues={vista.estadistica}
              antes={vista.estadistica_antes}
              resumen={vista.resumen}
            />
          </TabsContent>
          {vista.comparacion?.length ? (
            <TabsContent value="comparacion" className="mt-4">
              <ComparacionAntesDespues filas={vista.comparacion} />
            </TabsContent>
          ) : null}
        </Tabs>
      ) : (
        <VistaPrevia vista={vista} />
      )}

      <p className="flex gap-2 rounded-xl bg-primary-soft/60 p-3 text-sm text-foreground">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
        El instrumento quedó limpio. El siguiente paso es agregar sus metadatos.
      </p>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="outline" size="lg" onClick={onReajustar} disabled={reajustando}>
          <RotateCcw /> Volver a ajustar limpieza
        </Button>
        <Button size="lg" onClick={onContinuar}>
          Continuar a metadatos <ArrowRight />
        </Button>
      </div>
    </div>
  );
}

function VistaPrevia({ vista }: { vista: Vista }) {
  return (
    <section className="space-y-2">
      <h3 className="font-display text-base font-bold text-foreground">
        Vista previa del instrumento limpio
        <span className="ml-2 text-sm font-semibold text-muted-foreground">
          {vista.filas.length} de {vista.total_filas}{" "}
          {vista.forma === "turnos" ? "turnos" : "filas"}
        </span>
      </h3>
      <div className="max-h-[26rem] overflow-auto rounded-2xl border border-border bg-card">
        <table className="w-full min-w-max border-collapse text-sm">
          <thead className="sticky top-0 bg-primary-soft">
            <tr>
              {vista.columnas.map((c) => (
                <th
                  key={c}
                  scope="col"
                  className="max-w-[16rem] px-3 py-2 text-left text-xs font-bold text-foreground"
                >
                  <span className="line-clamp-2">{c}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {vista.filas.map((fila, i) => (
              <tr key={i} className="border-t border-border/70 odd:bg-muted/30">
                {fila.map((celda, j) => (
                  <td
                    key={j}
                    className={
                      // En entrevistas el texto del turno se lee completo (última columna).
                      vista.forma === "turnos" && j === fila.length - 1
                        ? "min-w-[18rem] max-w-[40rem] whitespace-normal px-3 py-2 align-top leading-relaxed text-foreground"
                        : "max-w-[16rem] truncate px-3 py-2 align-top text-foreground"
                    }
                    title={celda}
                  >
                    {celda || <span className="text-muted-foreground">—</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
