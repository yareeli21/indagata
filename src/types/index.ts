export const NIVELES_EDUCATIVOS = [
  "Preescolar",
  "Primaria",
  "Secundaria",
  "Media superior",
  "Superior",
] as const;

export type NivelEducativo = (typeof NIVELES_EDUCATIVOS)[number];

export const TIPOS_INSTRUMENTO = ["Encuesta", "Entrevista", "Prueba estandarizada"] as const;
export type TipoInstrumento = (typeof TIPOS_INSTRUMENTO)[number];

export type EstadoInstrumento = "Borrador" | "En revisión" | "Estandarizado";

export type Rol = "Investigador" | "Administrador";

export interface Usuario {
  id: string;
  usuario: string;
  nombre: string;
  rol: Rol;
  investigadorId: string;
}

export interface Investigador {
  id: string;
  nombre: string;
  institucion: string;
}

export interface Investigacion {
  id: string;
  nombre: string;
  propietarioId: string;
}

export interface Instrumento {
  id: string;
  titulo: string;
  tipo: TipoInstrumento;
  nivel: NivelEducativo;
  autorId: string;
  anio: number;
  reactivos: number;
  estado: EstadoInstrumento;
  descripcion: string;
  etiquetas: string[];
}

export interface Kpi {
  id: string;
  etiqueta: string;
  valor: string;
  variacion: number;
  detalle: string;
}

export interface Noticia {
  id: string;
  titulo: string;
  fecha: string;
  resumen: string;
}
