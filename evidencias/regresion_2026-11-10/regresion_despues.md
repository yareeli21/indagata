# Regresión del chat — modo «despues» (2026-11-10T07:21:18)

- Casos: 28
- Respuesta correcta: 78.6 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 100.0 %
- Tiempo por pregunta: mediana 44.92 s, máximo 120.95 s
- Plan completo correcto: 60.0 %; por campo: {'intencion': 88.0, 'filtros': 71.4, 'limite': 66.7, 'campos': 66.7, 'respondentes': 100.0, 'preguntas': 33.3, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 0.0}
- Mediana por etapa (ms): {'ejecucion': 11, 'redaccion': 20407, 'recuperacion': 333, 'verificacion': 2, 'interpretacion': 27204}
- Fallas: C06, C08, C11, C13, C21, C22

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 49.23 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | sí | 34.43 | plan:filtrar_respondentes:regenerada |
| C03 | por respondente (ordinal) | no | 58.79 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 45.85 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 48.86 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 27.22 | None |
| C07 | porcentaje en un nivel | no | 29.47 | plan:conteo_porcentaje:frase_dato |
| C08 | negación | no | 45.12 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | no | 48.65 | plan:filtrar_respondentes |
| C10 | por respondente (último) | sí | 55.87 | plan:datos_respondente:cita_inventada |
| C11 | resumen de una pregunta | no | 39.97 | plan:datos_respondente:cita_inventada |
| C12 | KPI | sí | 58.18 | plan:kpi |
| C13 | valor que no existe | no | 27.68 | plan:no_existe |
| C14 | ambigua | sí | 26.5 | plan:aclaracion |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 25.57 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 11.52 | None |
| C19 | uso de la plataforma | sí | 6.2 | None |
| C20 | comparar grupos de contexto | sí | 59.94 | plan:comparar_grupos:regenerada |
| C21 | porcentaje de un grupo | no | 44.72 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 58.03 | plan:comparar_grupos:cifras_corregidas |
| C23 | conteo binario | sí | 23.33 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | sí | 49.38 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 97.58 | plan:comparar_grupos:cifras_corregidas |
| C26 | hallazgo | sí | 120.95 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | no | 47.79 | plan:datos_respondente |
| C28 | semántica abierta | sí | 42.06 | None |
