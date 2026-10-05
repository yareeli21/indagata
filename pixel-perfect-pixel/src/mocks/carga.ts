import type { KpiSugerido, ReporteLimpieza } from "@/types";

export const reporteLimpiezaEjemplo: ReporteLimpieza = {
  duplicadosEliminados: 14,
  nulosTratados: 37,
  columnasNormalizadas: 9,
  cambios: [
    { campo: "Nombre de columna", antes: "Edad del Alumno ", despues: "edad_alumno" },
    { campo: "Nombre de columna", antes: "ESCUELA(Clave)", despues: "clave_escuela" },
    { campo: "Valor nulo", antes: "(vacío)", despues: "sin_respuesta" },
    { campo: "Escala", antes: "Muy de acuerdo / MDA / 5", despues: "5" },
    { campo: "Fecha", antes: "3/9/24", despues: "2024-09-03" },
    { campo: "Texto", antes: "  licenciatura ", despues: "Licenciatura" },
  ],
};

export const kpisSugeridosEjemplo: KpiSugerido[] = [
  { id: "ks-1", nombre: "Tasa de respuesta por plantel", coincidencia: 92 },
  { id: "ks-2", nombre: "Índice de comprensión lectora", coincidencia: 86 },
  { id: "ks-3", nombre: "Promedio de satisfacción docente", coincidencia: 78 },
  { id: "ks-4", nombre: "Porcentaje de reactivos omitidos", coincidencia: 71 },
  { id: "ks-5", nombre: "Distribución por nivel educativo", coincidencia: 64 },
];
