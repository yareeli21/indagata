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
                className={cn("cursor-pointer", ajeno && "bg-muted/40 text-muted-foreground")}>
                <TableCell className="max-w-64">
                  <p className={cn("font-medium", !ajeno && "text-foreground")}>{i.titulo}</p>
                  {ajeno && <div className="mt-1"><OtherResearcherBadge /></div>}
                </TableCell>
                <TableCell className={cn(ajeno && "opacity-70")}><TipoBadge tipo={i.tipo} /></TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {i.kpis.map((k) => (
                      <span key={k} className="whitespace-nowrap rounded-md border px-2 py-0.5 text-xs">{k}</span>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{i.nivel}</TableCell>
                <TableCell className="whitespace-nowrap">{formatearFecha(i.fecha)}</TableCell>
                <TableCell className="whitespace-nowrap">{nombre(i.autorId)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
