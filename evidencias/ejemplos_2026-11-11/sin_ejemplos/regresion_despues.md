# Regresión del chat — modo «despues» (2026-11-11T08:32:23)

- Casos: 28
- Respuesta correcta: 46.4 %
- Cifras correctas: 40.0 %
- Decisión de dominio correcta: 96.4 %
- Tiempo por pregunta: mediana 43.98 s, máximo 133.31 s
- Plan completo correcto: 24.0 %; por campo: {'intencion': 56.0, 'filtros': 14.3, 'limite': 0.0, 'campos': 66.7, 'respondentes': 50.0, 'preguntas': 33.3, 'nivel': 33.3, 'agrupar_por': 50.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 9, 'redaccion': 20153, 'recuperacion': 316, 'verificacion': 2, 'interpretacion': 25609}
- Fallas: C02, C05, C06, C07, C08, C09, C12, C13, C16, C18, C21, C22, C23, C24, C27

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 131.45 | plan:hallazgo:cita_inventada |
| C02 | filtro con límite y todas las respuestas | no | 53.91 | plan:conteo_porcentaje:frase_dato |
| C03 | por respondente (ordinal) | no | 47.61 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 29.38 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | no | 30.83 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 31.64 | plan:resumen_pregunta |
| C07 | porcentaje en un nivel | no | 33.06 | plan:conteo_porcentaje:cifras_corregidas |
| C08 | negación | no | 30.23 | plan:conteo_porcentaje:cifras_corregidas |
| C09 | límite y solo IDs | no | 43.0 | plan:datos_respondente |
| C10 | por respondente (último) | sí | 41.85 | plan:datos_respondente:inventada |
| C11 | resumen de una pregunta | sí | 44.95 | plan:resumen_pregunta:regenerada |
| C12 | KPI | no | 107.42 | plan:hallazgo:regenerada |
| C13 | valor que no existe | no | 19.47 | plan:no_existe |
| C14 | ambigua | no | 61.23 | plan:hallazgo |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | no | 42.43 | plan:hallazgo |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | no | 53.09 | plan:hallazgo |
| C19 | uso de la plataforma | sí | 9.4 | None |
| C20 | comparar grupos de contexto | sí | 69.32 | plan:comparar_grupos:regenerada |
| C21 | porcentaje de un grupo | no | 34.88 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 50.54 | plan:comparar_grupos:vacio |
| C23 | conteo binario | no | 48.78 | plan:conteo_porcentaje:cifras_corregidas |
| C24 | filtro con nivel y opción | no | 49.15 | plan:conteo_porcentaje |
| C25 | comparación entre instrumentos | no | 71.52 | None |
| C26 | hallazgo | sí | 133.31 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | no | 27.05 | plan:aclaracion |
| C28 | semántica abierta | no | 48.06 | None |
