import type { TipoPuntoEspacio } from "@/types";

/** Frases de ejemplo del buscador semántico (también las usa el recorrido). */
export const EJEMPLOS_BUSQUEDA = [
  "¿Por qué abandonan la carrera los estudiantes?",
  "Satisfacción con los profesores",
  "Producción científica y patentes",
];

export interface PasoRecorrido {
  titulo: string;
  texto: string;
  /** Tipo de punto que se resalta en el mapa durante el paso. */
  resaltar: TipoPuntoEspacio | null;
}

export const PASOS_RECORRIDO: PasoRecorrido[] = [
  {
    titulo: "Los KPIs",
    texto:
      "Cada círculo es un indicador educativo. Su color es su grupo temático: los KPIs que hablan de lo mismo quedan juntos y forman una zona.",
    resaltar: "kpi",
  },
  {
    titulo: "Los instrumentos",
    texto:
      "Cada rombo es un instrumento (sus metadatos y preguntas). Haz clic en uno para ver qué KPIs mide; «Alinear grupos» lo acerca a los de su tema.",
    resaltar: "instrumento",
  },
  {
    titulo: "Pregunta en vivo",
    texto:
      "Escribe una frase en el buscador: se convierte en vector, aparece como estrella y se une con lo más parecido. Así elige el chat sus fuentes.",
    resaltar: null,
  },
];
