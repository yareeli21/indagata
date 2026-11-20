# Regresión del chat — modo «despues» (2026-11-11T20:13:16)

- Casos: 28
- Respuesta correcta: 75.0 %
- Cifras correctas: 66.7 %
- Decisión de dominio correcta: 96.4 %
- Tiempo por pregunta: mediana 16.93 s, máximo 35.04 s
- Plan completo correcto: 72.0 %; por campo: {'intencion': 88.0, 'filtros': 42.9, 'limite': 100.0, 'campos': 100.0, 'respondentes': 100.0, 'preguntas': 66.7, 'nivel': 33.3, 'agrupar_por': 100.0, 'contexto': 100.0}
- Mediana por etapa (ms): {'ejecucion': 12, 'redaccion': 8211, 'recuperacion': 431, 'verificacion': 1546, 'interpretacion': 10410}
- Fallas: C02, C06, C08, C13, C14, C22, C24

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | sí | 22.6 | plan:hallazgo |
| C02 | filtro con límite y todas las respuestas | no | 24.11 | plan:datos_respondente:inventada |
| C03 | por respondente (ordinal) | sí | 18.21 | plan:datos_respondente |
| C04 | por respondente (ID y pregunta) | sí | 19.54 | plan:datos_respondente |
| C05 | filtros combinados (conteo) | sí | 16.98 | plan:conteo_porcentaje:frase_dato |
| C06 | seguimiento con historial | no | 20.99 | plan:hallazgo:negativa_corregida |
| C07 | porcentaje en un nivel | no | 9.63 | plan:conteo_porcentaje |
| C08 | negación | no | 19.52 | plan:conteo_porcentaje:cifras_completadas |
| C09 | límite y solo IDs | sí | 20.58 | plan:filtrar_respondentes:regenerada |
| C10 | por respondente (último) | sí | 13.79 | plan:datos_respondente |
| C11 | resumen de una pregunta | sí | 12.01 | plan:resumen_pregunta:cifras_completadas |
| C12 | KPI | sí | 35.04 | plan:kpi:inventada |
| C13 | valor que no existe | no | 11.95 | plan:aclaracion |
| C14 | ambigua | no | 14.91 | similitud máxima 0.29 < 0.3 |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 10.82 | plan:fuera_de_dominio |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | sí | 6.93 | None |
| C19 | uso de la plataforma | sí | 4.77 | None |
| C20 | comparar grupos de contexto | sí | 23.43 | plan:comparar_grupos:inventada |
| C21 | porcentaje de un grupo | sí | 16.16 | plan:conteo_porcentaje:frase_dato |
| C22 | comparar grupos de contexto | no | 23.99 | plan:comparar_grupos:inventada |
| C23 | conteo binario | sí | 7.97 | plan:conteo_porcentaje:frase_dato |
| C24 | filtro con nivel y opción | no | 17.83 | plan:conteo_porcentaje:frase_dato |
| C25 | comparación entre instrumentos | sí | 27.79 | plan:comparar_grupos:regenerada |
| C26 | hallazgo | sí | 30.19 | plan:hallazgo:inferencia |
| C27 | entrevista por participante | sí | 14.01 | plan:datos_respondente |
| C28 | semántica abierta | sí | 16.87 | None |
