# Experimento de modelos: resumen

Instrumento 127; 28 turnos en 14 casos. Generado con `scripts/modelos/reporte.py`.

## 1. Redactores (métricas sin juez, contra la referencia y humanas)

| Métrica | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct | gemma3:4b |
|---|---|---|---|---|
| Intención correcta | 54 % | 71 % | 54 % | 64 % |
| Plantillas indebidas | 7 | 8 | 10 | 2 |
| Respuestas redactadas por el modelo | 9 | 12 | 10 | 17 |
| Regeneraciones | 3 | 6 | 5 | 1 |
| Cifras con respaldo (redactadas) | 100 % | 100 % | 83 % | 100 % |
| Cifras sin respaldo | 0 | 0 | 2 | 0 |
| IDs inventados | 0 | 0 | 0 | 0 |
| Contexto suficiente (dato) | 25 % | 25 % | 42 % | 25 % |
| Exactitud de cifras | 59 % | 33 % | 78 % | 37 % |
| Criterios cumplidos | 18 % | 18 % | 27 % | 18 % |
| Similitud semántica | 0.497 | 0.426 | 0.534 | 0.493 |
| Latencia mediana (s) | 7.2 | 4.9 | 15.6 | 18.3 |
| Calificación humana media (0–2) | 0.643 | 0.857 | 1.071 | 1.071 |
| Respuestas «Bien» | 29 % | 29 % | 46 % | 43 % |
| Turnos calificados | 28 | 28 | 28 | 28 |

## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)

| Redactor \ Juez | gemma3:4b | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct |
|---|---|---|---|---|
| llama3.2:3b | 75 % | **73 %** | 52 % | 68 % |
| qwen2.5:3b | 76 % | 74 % | **56 %** | 69 % |
| qwen3:4b-instruct | 76 % | 74 % | 69 % | **71 %** |
| gemma3:4b | **78 %** | 74 % | 63 % | 78 % |

En negritas, la autoevaluación (el redactor se juzga a sí mismo).

**Fidelidad**

| Redactor \ Juez | gemma3:4b | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct |
|---|---|---|---|---|
| llama3.2:3b | 94 % | 80 % | 70 % | 71 % |
| qwen2.5:3b | 95 % | 89 % | 65 % | 71 % |
| qwen3:4b-instruct | 85 % | 77 % | 82 % | 73 % |
| gemma3:4b | 94 % | 76 % | 66 % | 87 % |

**Relevancia**

| Redactor \ Juez | gemma3:4b | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct |
|---|---|---|---|---|
| llama3.2:3b | 37 % | 44 % | 40 % | 46 % |
| qwen2.5:3b | 35 % | 39 % | 34 % | 46 % |
| qwen3:4b-instruct | 46 % | 50 % | 43 % | 50 % |
| gemma3:4b | 43 % | 45 % | 40 % | 48 % |

**Precisión del contexto**

| Redactor \ Juez | gemma3:4b | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct |
|---|---|---|---|---|
| llama3.2:3b | 100 % | 100 % | 43 % | 93 % |
| qwen2.5:3b | 100 % | 95 % | 70 % | 90 % |
| qwen3:4b-instruct | 100 % | 100 % | 83 % | 93 % |
| gemma3:4b | 100 % | 100 % | 83 % | 100 % |

## 3. Sesgo de autoevaluación

Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces (positivo = se califica mejor).

- llama3.2:3b: +8 puntos
- qwen2.5:3b: -16 puntos
- qwen3:4b-instruct: -2 puntos
- gemma3:4b: +7 puntos

## 4. ¿Se puede confiar en cada juez? (cruce)

Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.

| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |
|---|---|---|---|---|---|
| gemma3:4b | 0.159 (n=37) | 0.143 | 0.203 | 0.326 | 78 (78 calificadas) |
| llama3.2:3b | 0.043 (n=38) | 0.121 | 0.136 | 0.317 | 78 (78 calificadas) |
| qwen2.5:3b | 0.023 (n=39) | 0.108 | 0.266 | 0.281 | 78 (78 calificadas) |
| qwen3:4b-instruct | 0.033 (n=37) | 0.226 | 0.331 | 0.446 | 78 (78 calificadas) |

**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**

| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |
|---|---|---|---|---|
| gemma3:4b | 14 | 22 | 0 | 0 |
| llama3.2:3b | 14 | 22 | 0 | 0 |
| qwen2.5:3b | 13 | 11 | 1 | 11 |
| qwen3:4b-instruct | 14 | 20 | 0 | 2 |

**Acuerdo entre jueces** (Spearman del promedio sobre las mismas respuestas)

- gemma3:4b ~ llama3.2:3b: 0.584 (n=78)
- gemma3:4b ~ qwen2.5:3b: 0.429 (n=78)
- gemma3:4b ~ qwen3:4b-instruct: 0.371 (n=78)
- llama3.2:3b ~ qwen2.5:3b: 0.305 (n=78)
- llama3.2:3b ~ qwen3:4b-instruct: 0.399 (n=78)
- qwen2.5:3b ~ qwen3:4b-instruct: 0.31 (n=78)

## 5. ¿Falla del modelo o del código?

Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las métricas contra la referencia.

| Turno | Tipo | llama3.2:3b | qwen2.5:3b | qwen3:4b-instruct | gemma3:4b | Lectura |
|---|---|---|---|---|---|---|
| 1.1 | dato | ✗ | ✓ | ✓ | ✓ | depende del modelo |
| 1.2 | dato | ✗ | ✓ | ✓ | ✓ | depende del modelo |
| 1.3 | dato | ✗ | ✗ | ✓ | ✓ | depende del modelo |
| 2.1 | interpretativo | ✓ | ✓ | ✓ | ✗ | depende del modelo |
| 2.2 | interpretativo | ✗ | ✗ | ✗ | ✓ | depende del modelo |
| 2.3 | interpretativo | ✗ | ✗ | ✗ | ✓ | depende del modelo |
| 3.1 | interpretativo | ✗ | ✓ | ✗ | ✗ | depende del modelo |
| 4.1 | interpretativo | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 4.2 | interpretativo | ✗ | ✗ | ✓ | ✗ | depende del modelo |
| 5.1 | inexistente | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 6.1 | dato | ✓ | ✓ | ✓ | ✓ | bien en todos |
| 6.2 | inexistente | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 7.1 | dato | ✗ | ✗ | ✓ | ✗ | depende del modelo |
| 8.1 | control | ✓ | ✓ | ✓ | ✓ | bien en todos |
| 8.2 | control | ✓ | ✓ | ✓ | ✓ | bien en todos |
| 9.1 | dato | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 9.2 | dato | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 10.1 | interpretativo | ✗ | ✗ | ✓ | ✓ | depende del modelo |
| 10.2 | interpretativo | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 10.3 | interpretativo | ✗ | ✗ | ✗ | ✓ | depende del modelo |
| 10.4 | interpretativo | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 11.1 | dato | ✓ | ✗ | ✗ | ✗ | depende del modelo |
| 11.2 | dato | ✓ | ✓ | ✓ | ✓ | bien en todos |
| 12.1 | dato | ✗ | ✗ | ✗ | ✓ | depende del modelo |
| 12.2 | interpretativo | ✗ | ✗ | ✗ | ✗ | falla en todos: probable código |
| 13.1 | control | ✓ | ✗ | ✓ | ✗ | depende del modelo |
| 13.2 | control | ✓ | ✗ | ✗ | ✗ | depende del modelo |
| 14.1 | dato | ✗ | ✗ | ✓ | ✗ | depende del modelo |