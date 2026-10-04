import { instrumentos, investigadores } from "@/mocks/data";
import type {
  EstadoInstrumento,
  FormatoDescarga,
  Instrumento,
  InstrumentoRelacionado,
  Investigador,
  NivelEducativo,
  RazonCoincidencia,
  TipoInstrumento,
} from "@/types";
import { API_URL, ErrorHttp, pedir, simularRed } from "./client";

/**
 * DTO que devuelve el instrument-service (vía api-gateway). Espeja `Instrumento`
 * y añade el campo informativo `idProcesado` (= str(id_instrumento)), que el
 * frontend descarta al mapear a `Instrumento`.
 */
interface InstrumentoDTO {
  id: string;
  titulo: string;
  tipo: TipoInstrumento;
  nivel: NivelEducativo;
  autorId: string;
  anio: number;
  fecha: string;
  kpis: string[];
  reactivos: number;
  estado: EstadoInstrumento;
  descripcion: string;
  etiquetas: string[];
  idProcesado?: string | null;
}

/**
 * Mapeo campo a campo DTO→`Instrumento`. NO se usa spread para no colar
 * `idProcesado` (interfaz cerrada); se asignan explícitamente los 12 campos.
 */
function mapear(d: InstrumentoDTO): Instrumento {
  return {
    id: d.id,
    titulo: d.titulo,
    tipo: d.tipo,
    nivel: d.nivel,
    autorId: d.autorId,
    anio: d.anio,
    fecha: d.fecha,
    kpis: d.kpis,
    reactivos: d.reactivos,
    estado: d.estado,
    descripcion: d.descripcion,
    etiquetas: d.etiquetas,
  }; // d.idProcesado se ignora deliberadamente
}

export async function getInstrumentos(): Promise<Instrumento[]> {
  const dtos = await pedir<InstrumentoDTO[]>(`${API_URL}/instrumentos`, { auth: true });
  return dtos.map(mapear);
}

export async function getInstrumento(id: string): Promise<Instrumento | null> {
  try {
    const dto = await pedir<InstrumentoDTO>(`${API_URL}/instrumentos/${id}`, { auth: true });
    return mapear(dto);
  } catch (e) {
    if ((e as ErrorHttp).status === 404) return null;
    throw e;
  }
}

/** TODO: no hay servicio de investigadores en el backend de esta tanda. */
export function getInvestigadores(): Promise<Investigador[]> {
  return simularRed(investigadores);
}

/** Catálogo de KPIs usados por los instrumentos. GET /instrumentos/kpis/catalogo */
export function getCatalogoKpis(): Promise<string[]> {
  return pedir<string[]>(`${API_URL}/instrumentos/kpis/catalogo`, { auth: true });
}

/** DELETE /instrumentos/{id}: `id` es str(id_crudo) (borra también lo asociado). */
export function eliminarInstrumento(id: string): Promise<void> {
  return pedir<void>(`${API_URL}/instrumentos/${id}`, { method: "DELETE", auth: true });
}

/**
 * Descarga local a partir de los datos ya cargados.
 * TODO: cuando el backend exponga GET /instrumentos/{id}/descarga?formato=...,
 * reemplazar por una descarga real del binario/JSON almacenado.
 */
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
 * TODO: no hay endpoint de relacionados en el backend de esta tanda.
 * POST /instrumentos/relacionados { ids: string[] } (futuro).
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
