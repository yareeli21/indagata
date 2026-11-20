# Regresión del chat — modo «despues» (2026-11-11T07:56:33)

- Casos: 28
- Respuesta correcta: 78.6 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 100.0 %
- Tiempo por pregunta: mediana 42.78 s, máximo 107.26 s
- Plan completo correcto: 60.0 %; por campo: {'intencion': 88.0, 'filtros': 71.4, 'limite': 66.7, 'campos': 66.7, 'respondentes': 100.0, 'preguntas': 33.3, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 0.0}
- Mediana por etapa (ms): {'ejecucion': 23, 'redaccion': 18797, 'recuperacion': 312, 'verificacion': 2, 'interpretacion': 26929}
- Fallas: C06, C08, C11, C13, C21, C22

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 102.38 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | sí | 35.18 | plan:filtrar_respondentes |
| C03 | por respondente (ordinal) | no | 36.62 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 44.68 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 49.27 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 28.72 | None |
| C07 | porcentaje en un nivel | no | 25.3 | plan:conteo_porcentaje:frase_dato |
| C08 | negación | no | 47.0 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | no | 51.96 | plan:filtrar_respondentes:cifras_completadas |
| C10 | por respondente (último) | sí | 54.05 | plan:datos_respondente:cita_inventada |
| C11 | resumen de una pregunta | no | 39.2 | plan:datos_respondente:cita_inventada |
| C12 | KPI | sí | 56.9 | plan:kpi |
| C13 | valor que no existe | no | 27.34 | plan:no_existe |
| C14 | ambigua | sí | 26.39 | plan:aclaracion |
| C15 | fuera de dominio (regla) | sí | 0.1 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 25.52 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 14.58 | None |
| C19 | uso de la plataforma | sí | 6.51 | None |
| C20 | comparar grupos de contexto | sí | 60.18 | plan:comparar_grupos:regenerada |
| C21 | porcentaje de un grupo | no | 43.67 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 44.66 | plan:comparar_grupos |
| C23 | conteo binario | sí | 23.87 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | sí | 49.27 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 98.09 | plan:comparar_grupos:cifras_completadas |
| C26 | hallazgo | sí | 107.26 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | no | 48.68 | plan:datos_respondente |
| C28 | semántica abierta | sí | 41.88 | None |
