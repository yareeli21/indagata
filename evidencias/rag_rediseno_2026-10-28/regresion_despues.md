# Regresión del chat — modo «despues» (2026-10-28T13:28:29)

- Casos: 28
- Respuesta correcta: 96.4 %
- Cifras correctas: 100.0 %
- Decisión de dominio correcta: 100.0 %
- Tiempo por pregunta: mediana 28.23 s, máximo 55.57 s
- Plan completo correcto: 92.0 %; por campo: {'intencion': 92.0, 'filtros': 100.0, 'limite': 100.0, 'campos': 100.0, 'respondentes': 100.0, 'preguntas': 100.0, 'nivel': 100.0, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 14, 'redaccion': 8111, 'verificacion': 1988, 'interpretacion': 25568}
- Métricas RAGAS (media): {'fidelidad': 0.807, 'relevancia': 0.526, 'precisionContexto': 0.913}
- Fallas: C13

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 14.87 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | sí | 27.0 | plan:filtrar_respondentes:tabla |
| C03 | por respondente (ordinal) | sí | 25.05 | plan:datos_respondente:tabla |
| C04 | por respondente (ID y pregunta) | sí | 25.72 | plan:datos_respondente:tabla |
| C05 | filtros combinados (conteo) | sí | 36.38 | plan:conteo_porcentaje:regenerada |
| C06 | seguimiento con historial | sí | 34.53 | plan:conteo_porcentaje |
| C07 | porcentaje en un nivel | sí | 35.5 | plan:conteo_porcentaje:cifras_completadas |
| C08 | negación | sí | 34.64 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | sí | 26.83 | plan:filtrar_respondentes:tabla |
| C10 | por respondente (último) | sí | 25.95 | plan:datos_respondente:tabla |
| C11 | resumen de una pregunta | sí | 36.35 | plan:resumen_pregunta:cifras_corregidas |
| C12 | KPI | sí | 55.57 | plan:kpi:inventada |
| C13 | valor que no existe | no | 33.31 | plan:conteo_porcentaje:regenerada |
| C14 | ambigua | sí | 25.23 | plan:aclaracion |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | no | 1.45 | plan:aclaracion_ajena |
| C17 | reidentificación | sí | 0.08 | regla:privacidad |
| C18 | metodología | sí | 13.58 | None |
| C19 | uso de la plataforma | sí | 13.84 | None |
| C20 | comparar grupos de contexto | sí | 25.83 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 30.13 | plan:conteo_porcentaje:cifras_completadas |
| C22 | comparar grupos de contexto | sí | 43.55 | plan:comparar_grupos:inventada |
| C23 | conteo binario | sí | 35.57 | plan:conteo_porcentaje:cifras_corregidas |
| C24 | filtro con nivel y opción | sí | 36.29 | plan:conteo_porcentaje:cifras_completadas |
| C25 | comparación entre instrumentos | sí | 50.09 | plan:comparar_grupos:inventada |
| C26 | hallazgo | sí | 29.45 | plan:hallazgo |
| C27 | entrevista por participante | sí | 20.59 | plan:datos_respondente:tabla |
| C28 | semántica abierta | sí | 44.63 | None |
