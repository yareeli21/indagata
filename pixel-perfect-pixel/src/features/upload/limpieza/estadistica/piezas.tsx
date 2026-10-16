import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { claseNivel, pct } from "./formato";

/** Etiqueta de interpretación (excelente, aceptable, difícil…) con su tono. */
export function Nivel({ nivel }: { nivel: string | null | undefined }) {
  if (!nivel) return null;
  return (
    <span
      className={cn(
        "inline-flex w-fit rounded-full px-2 py-0.5 text-xs font-bold capitalize",
        claseNivel(nivel),
      )}
    >
      {nivel}
    </span>
  );
}

/** Barra horizontal de una frecuencia relativa. */
export function Barra({
  etiqueta,
  n,
  proporcion,
  destacada = false,
}: {
  etiqueta: string;
  n: number;
  proporcion: number;
  destacada?: boolean;
}) {
  return (
    <li className="grid grid-cols-[minmax(0,9rem)_1fr_auto] sm:grid-cols-[minmax(0,12rem)_1fr_auto] items-center gap-2 text-xs">
      <span
        className={cn("truncate", destacada ? "font-bold text-foreground" : "text-foreground")}
        title={etiqueta}
      >
        {etiqueta}
      </span>
      <span className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
        <span
          className={cn("block h-full rounded-full", destacada ? "bg-success" : "bg-primary")}
          style={{ width: `${Math.max(0, Math.min(1, proporcion)) * 100}%` }}
        />
      </span>
      <span className="tabular-nums text-muted-foreground">
        {n} · {pct(proporcion)}
      </span>
    </li>
  );
}

/** Contenedor desplazable para tablas anchas (no rompe el ancho en móvil). */
export function TablaDesplazable({
  children,
  etiqueta,
}: {
  children: ReactNode;
  etiqueta: string;
}) {
  return (
    <div
      className="overflow-x-auto rounded-2xl border border-border bg-card"
      role="region"
      aria-label={etiqueta}
      tabIndex={0}
    >
      <table className="w-full min-w-max border-collapse text-sm">{children}</table>
    </div>
  );
}

export function Th({
  children,
  titulo,
  alinear = "izquierda",
}: {
  children: ReactNode;
  titulo?: string;
  alinear?: "izquierda" | "derecha";
}) {
  return (
    <th
      scope="col"
      title={titulo}
      className={cn(
        "bg-primary-soft px-3 py-2 text-xs font-bold text-foreground",
        alinear === "derecha" ? "text-right" : "text-left",
        titulo && "cursor-help underline decoration-dotted underline-offset-2",
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  alinear = "izquierda",
  className,
}: {
  children: ReactNode;
  alinear?: "izquierda" | "derecha";
  className?: string | undefined;
}) {
  return (
    <td
      className={cn(
        "px-3 py-2 align-top text-foreground",
        alinear === "derecha" && "text-right tabular-nums",
        className,
      )}
    >
      {children}
    </td>
  );
}

/** Cifra destacada con su etiqueta y una ayuda opcional. */
export function Cifra({
  etiqueta,
  valor,
  ayuda,
  children,
}: {
  etiqueta: string;
  valor: ReactNode;
  ayuda?: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border border-border bg-card p-4" title={ayuda}>
      <span className="text-xs font-semibold text-muted-foreground">{etiqueta}</span>
      <span className="font-display text-2xl font-bold tabular-nums text-foreground">{valor}</span>
      {children}
    </div>
  );
}

export function Subtitulo({ children, detalle }: { children: ReactNode; detalle?: ReactNode }) {
  return (
    <h4 className="font-display text-base font-bold text-foreground">
      {children}
      {detalle && (
        <span className="ml-2 text-sm font-semibold text-muted-foreground">{detalle}</span>
      )}
    </h4>
  );
}
