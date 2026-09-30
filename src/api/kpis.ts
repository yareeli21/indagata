import { kpis, noticias } from "@/mocks/data";
import type { Kpi, Noticia } from "@/types";
import { simularRed } from "./client";

export function getKpis(): Promise<Kpi[]> {
  return simularRed(kpis);
}

export function getNoticias(): Promise<Noticia[]> {
  return simularRed(noticias);
}
