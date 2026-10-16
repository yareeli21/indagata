import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import type { ComparacionMetrica } from "@/types";
import { segunFormato } from "./formato";
import { TablaDesplazable, Td, Th } from "./piezas";

/** Métricas de calidad del archivo tal como llegó y del instrumento limpio. */
export function ComparacionAntesDespues({ filas }: { filas: ComparacionMetrica[] }) {
  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground">
        «Antes» es el archivo tal como lo subiste; «Después», el instrumento limpio con tus
        decisiones aplicadas.
      </p>
      <TablaDesplazable etiqueta="Métricas antes y después de la limpieza">
        <thead>
          <tr>
            <Th>Métrica</Th>
            <Th alinear="derecha">Antes</Th>
            <Th alinear="derecha">Después</Th>
            <Th alinear="derecha">Cambio</Th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => {
            const cambio =
              f.antes !== null && f.despues !== null ? Number(f.despues) - Number(f.antes) : null;
            return (
              <tr key={f.metrica} className="border-t border-border/70">
                <Td>{f.metrica}</Td>
                <Td alinear="derecha" className="text-muted-foreground">
                  {segunFormato(f.antes, f.formato)}
                </Td>
                <Td alinear="derecha" className="font-semibold">
                  {segunFormato(f.despues, f.formato)}
                </Td>
                <Td alinear="derecha">
                  {cambio === null || Math.abs(cambio) < 1e-9 ? (
                    <Minus
                      className="ml-auto size-4 text-muted-foreground"
                      aria-label="Sin cambio"
                    />
                  ) : (
                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                      {cambio > 0 ? (
                        <ArrowUp className="size-3.5" aria-hidden />
                      ) : (
                        <ArrowDown className="size-3.5" aria-hidden />
                      )}
                      {segunFormato(Math.abs(cambio), f.formato)}
                    </span>
                  )}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </TablaDesplazable>
    </div>
  );
}
