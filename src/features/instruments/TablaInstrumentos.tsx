import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { OtherResearcherBadge } from "@/components/shared/OtherResearcherBadge";
import { cn } from "@/lib/utils";
import type { Instrumento, Investigador } from "@/types";
import { TipoBadge } from "./TipoBadge";
import { formatearFecha } from "./filtros";

interface TablaInstrumentosProps {
  instrumentos: Instrumento[];
  investigadores: Investigador[];
  miId: string;
  onSeleccionar: (i: Instrumento) => void;
}

export function TablaInstrumentos({ instrumentos, investigadores, miId, onSeleccionar }: TablaInstrumentosProps) {
  const nombre = (id: string) => investigadores.find((x) => x.id === id)?.nombre ?? "—";
  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Título</TableHead>
            <TableHead>Tipo</TableHead>
            <TableHead>KPIs</TableHead>
            <TableHead>Nivel educativo</TableHead>
            <TableHead>Fecha</TableHead>
            <TableHead>Investigador</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {instrumentos.map((i) => {
            const ajeno = i.autorId !== miId;
            return (
              <TableRow key={i.id} onClick={() => onSeleccionar(i)}
                className={cn("cursor-pointer transition-colors", ajeno ? "bg-muted/40 opacity-75 hover:opacity-90 hover:bg-muted/60" : "hover:bg-muted/30")}>
                <TableCell className="max-w-64">
                  <p className={cn("font-medium", ajeno ? "text-muted-foreground" : "text-foreground")}>{i.titulo}</p>
                </TableCell>
                <TableCell><TipoBadge tipo={i.tipo} /></TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {i.kpis.map((k) => (
                      <span key={k} className={cn("whitespace-nowrap rounded-md border px-2 py-0.5 text-xs", ajeno && "border-border/50 text-muted-foreground")}>{k}</span>
                    ))}
                  </div>
                </TableCell>
                <TableCell className={cn(ajeno && "text-muted-foreground")}>{i.nivel}</TableCell>
                <TableCell className={cn("whitespace-nowrap", ajeno && "text-muted-foreground")}>{formatearFecha(i.fecha)}</TableCell>
                <TableCell className="whitespace-nowrap">
                  <div className="flex flex-col gap-1">
                    <span className={cn(ajeno && "text-muted-foreground")}>{nombre(i.autorId)}</span>
                    {ajeno && <OtherResearcherBadge />}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
