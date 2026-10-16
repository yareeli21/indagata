import { AlertTriangle, CheckCircle2, Info, Lightbulb, OctagonAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type { FraseResumen } from "@/types";
import { AYUDA, CLASE_TONO } from "./formato";

const ESTILO: Record<
  FraseResumen["nivel"],
  { icono: typeof Info; clase: string; etiqueta: string }
> = {
  bien: { icono: CheckCircle2, clase: CLASE_TONO.bien, etiqueta: "En orden" },
  info: { icono: Info, clase: CLASE_TONO.medio, etiqueta: "Dato" },
  atencion: { icono: AlertTriangle, clase: CLASE_TONO.alerta, etiqueta: "Conviene revisar" },
  alerta: { icono: OctagonAlert, clase: CLASE_TONO.mal, etiqueta: "Posible problema" },
};

/** Glosario en lenguaje sencillo (el detalle completo está en markdowns/METRICAS_LIMPIEZA.md). */
const GLOSARIO: { termino: string; texto: string }[] = [
  { termino: "Media", texto: "El promedio de las respuestas." },
  {
    termino: "Mediana",
    texto:
      "El valor del centro: la mitad respondió menos y la otra mitad más. No se mueve con valores extremos.",
  },
  {
    termino: "Desviación estándar",
    texto:
      "Qué tan diferentes son las respuestas entre sí. En una escala de 1 a 5, alrededor de 1 indica opiniones variadas.",
  },
  {
    termino: "Q1 – Q3",
    texto: "Entre estos dos valores está la mitad central de las respuestas.",
  },
  { termino: "Asimetría", texto: AYUDA.asimetria },
  { termino: "Curtosis", texto: AYUDA.curtosis },
  { termino: "Atípicos", texto: AYUDA.atipicos },
  { termino: "Alfa de Cronbach", texto: AYUDA.alfa },
  { termino: "Correlación ítem-total", texto: AYUDA.itemTotal },
  { termino: "Alfa si se elimina el ítem", texto: AYUDA.alfaSiSeElimina },
  { termino: "KR-20", texto: AYUDA.kr20 },
  { termino: "Dificultad (p)", texto: AYUDA.dificultad },
  { termino: "Discriminación (D)", texto: AYUDA.discriminacion },
  { termino: "Punto-biserial", texto: AYUDA.puntoBiserial },
];

export function GlosarioEstadistico() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="link" size="sm" className="h-auto px-0">
          ¿Qué significa cada medida?
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Qué significa cada medida</DialogTitle>
          <DialogDescription>
            Estas medidas sirven para comprobar que los datos limpios tienen sentido antes de pasar
            a metadatos.
          </DialogDescription>
        </DialogHeader>
        <dl className="space-y-3 text-sm">
          {GLOSARIO.map((g) => (
            <div key={g.termino}>
              <dt className="font-bold text-foreground">{g.termino}</dt>
              <dd className="text-muted-foreground">{g.texto}</dd>
            </div>
          ))}
        </dl>
      </DialogContent>
    </Dialog>
  );
}

/** «En pocas palabras»: lo más importante de las medidas, explicado sin tecnicismos. */
export function ResumenEstadistica({ frases }: { frases: FraseResumen[] }) {
  return (
    <section
      className="space-y-3 rounded-2xl border border-primary/15 bg-primary-soft/40 p-4 sm:p-5"
      aria-labelledby="resumen-estadistico"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4
          id="resumen-estadistico"
          className="flex items-center gap-2 font-display text-base font-bold text-foreground"
        >
          <Lightbulb className="size-5 text-primary" aria-hidden /> En pocas palabras
        </h4>
        <GlosarioEstadistico />
      </div>
      <ul className="space-y-2">
        {frases.map((f, i) => {
          const { icono: Icono, clase, etiqueta } = ESTILO[f.nivel] ?? ESTILO.info;
          return (
            <li key={i} className="flex items-start gap-3 text-sm text-foreground">
              <span
                className={cn("mt-0.5 grid size-6 shrink-0 place-items-center rounded-full", clase)}
                title={etiqueta}
              >
                <Icono className="size-3.5" aria-hidden />
                <span className="sr-only">{etiqueta}:</span>
              </span>
              <span className="min-w-0">{f.texto}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
