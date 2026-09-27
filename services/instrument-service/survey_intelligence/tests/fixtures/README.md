# Fixtures reales del SIS (Nivel 1)

Exportaciones reales de encuestas usadas como casos de aceptación end-to-end.
Todas son Nivel 1 (sin codebook): todo se interpreta desde encabezados + valores.

| Archivo | Plataforma | Qué ejercita |
|---|---|---|
| `limesurvey_participacion.csv` | LimeSurvey | Matriz Likert de 33 ítems con notación `tronco [ítem]`; error de escala `En deesacuerdo` (distancia de edición 1); fila de respuesta vacía/abandonada; `Start language=en` con contenido en español. |
| `limesurvey_salud_mental.csv` | LimeSurvey | Tipos mixtos: binaria `Sí/No`, opción múltiple explotada en columnas `[opción]`, matriz de evaluación, y texto libre; nulos estructurales por lógica de salto condicional; mezcla `Yes/No` (inglés) con `Sí/No` (español). |
| `msforms_graduacion.csv` | Microsoft Forms | Notación de matriz `.subítem`; celdas `multi_select` colapsadas con `;`; columnas administrativas `Id/Hora de inicio/Hora de finalización/Correo electrónico/Nombre`; saltos de línea embebidos en encabezados; escala explicada en el texto (`1=Muy improbable y 5=Muy probable`). |
| `googleforms_extracurriculares.xlsx` | Google Forms | Formato `.xlsx` real (ZIP+XML, requiere openpyxl); firma administrativa mínima: una sola columna `Marca temporal` (datetime nativo); celdas `multi_select` colapsadas con `, ` (coma+espacio, distinto de Microsoft Forms); encabezados que son preguntas completas (sin matriz). |

## Nota sobre codificación

`msforms_graduacion.csv` se transcribió a UTF-8 limpio (el original llegó con mojibake
Latin-1/CP1252). El reader del SIS debe, aun así, detectar codificación en tiempo de
ejecución (UTF-8, UTF-8-BOM, CP1252/Latin-1), porque las exportaciones reales varían.
