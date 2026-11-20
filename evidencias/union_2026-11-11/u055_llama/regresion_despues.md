# Regresión del chat — modo «despues» (2026-11-11T18:47:47)

- Casos: 28
- Respuesta correcta: 75.0 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 96.4 %
- Tiempo por pregunta: mediana 17.12 s, máximo 37.54 s
- Plan completo correcto: 72.0 %; por campo: {'intencion': 88.0, 'filtros': 42.9, 'limite': 100.0, 'campos': 100.0, 'respondentes': 100.0, 'preguntas': 66.7, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 9, 'redaccion': 9308, 'recuperacion': 355, 'verificacion': 2989, 'interpretacion': 10288}
- Fallas: C02, C06, C08, C13, C14, C22, C24

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 28.98 | plan:hallazgo:regenerada |
| C02 | filtro con límite y todas las respuestas | no | 22.73 | plan:datos_respondente:inventada |
| C03 | por respondente (ordinal) | sí | 19.14 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 20.19 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 17.72 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 22.66 | plan:hallazgo:negativa_corregida |
| C07 | porcentaje en un nivel | no | 9.75 | plan:conteo_porcentaje |
| C08 | negación | no | 23.43 | plan:conteo_porcentaje:cifras_corregidas |
| C09 | límite y solo IDs | sí | 19.97 | plan:filtrar_respondentes:cifras_completadas |
| C10 | por respondente (último) | sí | 13.88 | plan:datos_respondente |
| C11 | resumen de una pregunta | sí | 9.7 | plan:resumen_pregunta:regenerada |
| C12 | KPI | sí | 37.54 | plan:kpi:inventada |
| C13 | valor que no existe | no | 10.7 | plan:aclaracion |
| C14 | ambigua | no | 13.46 | similitud máxima 0.29 < 0.3 |
| C15 | fuera de dominio (regla) | sí | 0.08 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 10.66 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 8.44 | None |
| C19 | uso de la plataforma | sí | 4.22 | None |
| C20 | comparar grupos de contexto | sí | 22.7 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 16.16 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 24.68 | plan:comparar_grupos:inventada |
| C23 | conteo binario | sí | 10.2 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | no | 17.89 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 29.35 | plan:comparar_grupos:cifras_completadas |
| C26 | hallazgo | sí | 31.8 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | sí | 13.15 | plan:datos_respondente |
| C28 | semántica abierta | sí | 16.51 | None |
