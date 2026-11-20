# Regresión del chat — modo «antes» (2026-10-28T13:39:44)

- Casos: 28
- Respuesta correcta: 53.6 %
- Cifras correctas: 46.7 %
- Decisión de dominio correcta: 85.7 %
- Tiempo por pregunta: mediana 11.84 s, máximo 20.14 s
- Mediana por etapa (ms): {'redaccion': 11325, 'verificacion': 0}
- Métricas RAGAS (media): {'fidelidad': 0.846, 'relevancia': 0.561, 'precisionContexto': 0.903}
- Fallas: C01, C03, C06, C07, C08, C10, C11, C13, C14, C18, C20, C22, C25

| Caso | Categoría | ¿Bien? | s | Motivo |
|---|---|---|---|---|
| C01 | hallazgo | no | 12.34 | None |
| C02 | filtro con límite y todas las respuestas | sí | 11.95 | estructurada:filtro:negativa_corregida |
| C03 | por respondente (ordinal) | no | 8.1 | clasificador: No se proporcionó información sobre los respuestas de un respondente |
| C04 | por respondente (ID y pregunta) | sí | 5.61 | estructurada:respuesta |
| C05 | filtros combinados (conteo) | sí | 14.46 | estructurada:filtro:negativa_corregida |
| C06 | seguimiento con historial | no | 11.55 | estructurada:filtro:cifras_completadas |
| C07 | porcentaje en un nivel | no | 11.73 | estructurada:pct_nivel:cifras_completadas |
| C08 | negación | no | 15.63 | None |
| C09 | límite y solo IDs | sí | 12.14 | estructurada:filtro:negativa_corregida |
| C10 | por respondente (último) | no | 8.31 | clasificador: No tengo acceso a información de respuestas previas |
| C11 | resumen de una pregunta | no | 12.16 | estructurada:filtro:negativa_corregida |
| C12 | KPI | sí | 13.4 | None |
| C13 | valor que no existe | no | 12.61 | el modelo no encontró la respuesta en el contexto |
| C14 | ambigua | no | 1.9 | clasificador: No es relevante para el dominio de la educación |
| C15 | fuera de dominio (regla) | sí | 0.07 | regla:fuera |
| C16 | fuera de dominio (plan) | sí | 0.22 | similitud máxima 0.19 < 0.3 |
| C17 | reidentificación | sí | 0.07 | regla:privacidad |
| C18 | metodología | no | 3.33 | None |
| C19 | uso de la plataforma | sí | 13.41 | None |
| C20 | comparar grupos de contexto | no | 1.56 | estructurada:pct_nivel:negativa_corregida |
| C21 | porcentaje de un grupo | sí | 11.67 | estructurada:pct_nivel |
| C22 | comparar grupos de contexto | no | 12.11 | estructurada:filtro:cifras_completadas |
| C23 | conteo binario | sí | 11.49 | estructurada:filtro |
| C24 | filtro con nivel y opción | sí | 13.28 | estructurada:filtro:cifras_completadas |
| C25 | comparación entre instrumentos | no | 20.14 | None |
| C26 | hallazgo | sí | 0.38 | estructurada:patrones |
| C27 | entrevista por participante | sí | 18.67 | estructurada:dijo |
| C28 | semántica abierta | sí | 14.55 | None |
