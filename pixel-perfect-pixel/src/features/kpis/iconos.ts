import {
  Award,
  BarChart2,
  BookOpen,
  Briefcase,
  Calculator,
  ClipboardCheck,
  Heart,
  Home,
  Laptop,
  MessageCircle,
  Monitor,
  Shield,
  Smile,
  Users,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Mapa único de íconos de Lucide usados por el catálogo de KPIs. Es la fuente de
 * verdad compartida por `TarjetaKpi`/`DetalleKpi` (render) y la heurística
 * `elegirIcono` de `src/api/kpis.ts` (selección). El fallback obligatorio es
 * `BarChart2`; `ChartBar` no existe en lucide-react.
 */
export const ICONOS: Record<string, LucideIcon> = {
  Award,
  BarChart2,
  BookOpen,
  Briefcase,
  Calculator,
  ClipboardCheck,
  Heart,
  Home,
  Laptop,
  MessageCircle,
  Monitor,
  Shield,
  Smile,
  Users,
  Zap,
};

/** Las 15 claves válidas del mapa `ICONOS`, para blindar `elegirIcono` (FR-5.4). */
export const ICONOS_VALIDOS = new Set<string>(Object.keys(ICONOS));
