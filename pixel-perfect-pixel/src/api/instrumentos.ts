import { instrumentos, investigadores } from "@/mocks/data";
import type {
  FormatoDescarga,
  Instrumento,
  InstrumentoRelacionado,
  Investigador,
  RazonCoincidencia,
} from "@/types";
import { simularRed } from "./client";

export function getInstrumentos(): Promise<Instrumento[]> {
  return simularRed([...instrumentos]);
}

export function getInstrumento(id: string): Promise<Instrumento | null> {
  return simularRed(instrumentos.find((i) => i.id === id) ?? null);
}

export function getInvestigadores(): Promise<Investigador[]> {
  return simularRed(investigadores);
}

/** Catálogo de KPIs usados por los instrumentos. Futuro: GET /kpis/catalogo */
export function getCatalogoKpis(): Promise<string[]> {
  return simularRed([...new Set(instrumentos.flatMap((i) => i.kpis))].sort());
}

/** Futuro: DELETE /instrumentos/{id} (borra también todo lo asociado). */
export function eliminarInstrumento(id: string): Promise<void> {
  const idx = instrumentos.findIndex((i) => i.id === id);
  if (idx >= 0) instrumentos.splice(idx, 1);
  return simularRed(undefined, 500);
}

/** Futuro: GET /instrumentos/{id}/descarga?formato=... */
export function descargarInstrumento(id: string, formato: FormatoDescarga): Promise<void> {
  const ins = instrumentos.find((i) => i.id === id);
  if (ins) {
    const contenido =
      formato === "json" ? JSON.stringify(ins, null, 2) : `${ins.titulo}\n\n${ins.descripcion}`;
    const ext = formato === "crudo" ? "txt" : formato;
    const url = URL.createObjectURL(new Blob([contenido]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ins.id}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return simularRed(undefined, 200);
}

/**
 * Futuro: POST /instrumentos/relacionados { ids: string[] }
 * Devuelve instrumentos de otros autores que comparten KPIs, nivel o descripción
 * con el conjunto seleccionado. Simulación determinista basada en coincidencias reales.
 */
export function buscarRelacionados(
  seleccionIds: string[],
  autorId: string,
): Promise<InstrumentoRelacionado[]> {
  const seleccionados = instrumentos.filter((i) => seleccionIds.includes(i.id));
  const ajenos = instrumentos.filter((i) => i.autorId !== autorId);

  const resultados: InstrumentoRelacionado[] = [];

  for (const ajeno of ajenos) {
    const razones: RazonCoincidencia[] = [];
    const coincideCon: string[] = [];

    for (const propio of seleccionados) {
      // KPIs compartidos
      const kpisCompartidos = propio.kpis.filter((k) => ajeno.kpis.includes(k));
      for (const k of kpisCompartidos) {
        if (!razones.some((r) => r.etiqueta === `Mismo KPI: ${k}`)) {
          razones.push({ tipo: "kpi", etiqueta: `Mismo KPI: ${k}` });
        }
      }
      // Nivel educativo compartido
      if (propio.nivel === ajeno.nivel) {
        if (!razones.some((r) => r.tipo === "nivel")) {
          razones.push({ tipo: "nivel", etiqueta: `Mismo nivel: ${ajeno.nivel}` });
        }
      }
      // Similitud de descripción (simulada por palabras en común)
      const palabrasPropio = new Set(
        propio.descripcion
          .toLowerCase()
          .split(/\W+/)
          .filter((w) => w.length > 4),
      );
      const palabrasAjeno = ajeno.descripcion
        .toLowerCase()
        .split(/\W+/)
        .filter((w) => w.length > 4);
      const coincidencias = palabrasAjeno.filter((w) => palabrasPropio.has(w)).length;
      const total = Math.max(palabrasPropio.size, palabrasAjeno.length, 1);
      const pct = Math.round((coincidencias / total) * 100);
      if (pct >= 20) {
        if (!razones.some((r) => r.tipo === "descripcion")) {
          razones.push({ tipo: "descripcion", etiqueta: `Descripción similar: ${pct}%` });
        }
      }
      if (kpisCompartidos.length > 0 || propio.nivel === ajeno.nivel || pct >= 20) {
        if (!coincideCon.includes(propio.id)) coincideCon.push(propio.id);
      }
    }

    if (razones.length === 0) continue;

    const nivel = razones.length >= 3 ? "alta" : razones.length === 2 ? "media" : "baja";

    resultados.push({ instrumento: ajeno, nivel, coincideCon, razones });
  }

  // Orden: alta → media → baja, luego por título
  resultados.sort((a, b) => {
    const ord: Record<string, number> = { alta: 0, media: 1, baja: 2 };
    return (
      (ord[a.nivel] ?? 3) - (ord[b.nivel] ?? 3) ||
      a.instrumento.titulo.localeCompare(b.instrumento.titulo)
    );
  });

  return simularRed(resultados, 1200);
}
