# Regresión del chat — modo «despues» (2026-10-28T12:50:00)

- Casos: 28
- Respuesta correcta: 71.4 %
- Cifras correctas: 60.0 %
- Decisión de dominio correcta: 100.0 %
- Tiempo por pregunta: mediana 5.51 s, máximo 32.49 s
- Plan completo correcto: 76.9 %; por campo: {'intencion': 92.3, 'filtros': 85.7, 'limite': 100.0, 'campos': 83.3, 'respondentes': 100.0, 'preguntas': 83.3, 'nivel': 33.3, 'agrupar_por': 100.0}
- Mediana por etapa (ms): {'ejecucion': 18, 'redaccion': 4332, 'verificacion': 1817, 'interpretacion': 1646}
- Fallas: C08, C10, C13, C20, C21, C22, C24, C25

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 32.49 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | sí | 2.48 | plan:filtrar_respondentes:tabla |
| C03 | por respondente (ordinal) | sí | 1.69 | plan:datos_respondente:tabla |
| C04 | por respondente (ID y pregunta) | sí | 1.64 | plan:datos_respondente:tabla |
| C05 | filtros combinados (conteo) | sí | 4.79 | plan:conteo_porcentaje |
| C06 | seguimiento con historial | sí | 6.34 | plan:conteo_porcentaje |
| C07 | porcentaje en un nivel | sí | 6.18 | plan:conteo_porcentaje:cifras_completadas |
| C08 | negación | no | 5.72 | plan:conteo_porcentaje:regenerada |
| C09 | límite y solo IDs | sí | 2.35 | plan:filtrar_respondentes:tabla |
| C10 | por respondente (último) | no | 1.61 | plan:datos_respondente:tabla |
| C11 | resumen de una pregunta | sí | 8.21 | plan:resumen_pregunta:cifras_corregidas |
| C12 | KPI | sí | 19.4 | plan:kpi:regenerada |
| C13 | valor que no existe | no | 2.43 | plan:aclaracion |
| C14 | ambigua | sí | 1.3 | plan:aclaracion |
| C15 | fuera de dominio (regla) | sí | 0.06 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 0.94 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 9.34 | None |
| C19 | uso de la plataforma | no | 3.91 | None |
| C20 | comparar grupos de contexto | no | 13.38 | plan:comparar_grupos:cifras_corregidas |
| C21 | porcentaje de un grupo | no | 5.31 | plan:conteo_porcentaje:regenerada |
| C22 | comparar grupos de contexto | no | 15.55 | plan:comparar_grupos |
| C23 | conteo binario | sí | 6.19 | plan:conteo_porcentaje:cifras_corregidas |
| C24 | filtro con nivel y opción | no | 13.65 | plan:conteo_porcentaje |
| C25 | comparación entre instrumentos | no | 9.46 | plan:aclaracion |
| C26 | hallazgo | sí | 8.63 | plan:hallazgo |
| C27 | entrevista por participante | no | 4.34 | plan:datos_respondente:tabla |
| C28 | semántica abierta | sí | 7.38 | None |
