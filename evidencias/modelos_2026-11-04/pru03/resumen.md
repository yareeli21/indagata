# Experimento de modelos: resumen

Instrumento 130; 22 turnos en 12 casos. Generado con `scripts/modelos/reporte.py`.

## 1. Redactores (métricas sin juez, contra la referencia y humanas)

| Métrica | qwen3:4b-instruct | gemma3:4b |
|---|---|---|
| Intención correcta | 64 % | 59 % |
| Plantillas indebidas | 7 | 2 |
| Respuestas redactadas por el modelo | 8 | 10 |
| Regeneraciones | 5 | 1 |
| Cifras con respaldo (redactadas) | 100 % | 100 % |
| Cifras sin respaldo | 0 | 0 |
| IDs inventados | 0 | 0 |
| Contexto suficiente (dato) | 64 % | 64 % |
| Exactitud de cifras | 64 % | 46 % |
| Criterios cumplidos | 100 % | 100 % |
| Similitud semántica | 0.436 | 0.385 |
| Latencia mediana (s) | 12.7 | 18.0 |
| Calificación humana media (0–2) | 1.136 | 1.045 |
| Respuestas «Bien» | 50 % | 46 % |
| Turnos calificados | 22 | 22 |

## 2. Matriz redactor × juez (promedio de fidelidad, relevancia y precisión)

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | **81 %** |
| gemma3:4b | 82 % |

En negritas, la autoevaluación (el redactor se juzga a sí mismo).

**Fidelidad**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 92 % |
| gemma3:4b | 93 % |

**Relevancia**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 52 % |
| gemma3:4b | 52 % |

**Precisión del contexto**

| Redactor \ Juez | qwen3:4b-instruct |
|---|---|
| qwen3:4b-instruct | 100 % |
| gemma3:4b | 100 % |

## 3. Sesgo de autoevaluación

Promedio cuando el redactor se juzga a sí mismo menos el promedio que le dan los demás jueces (positivo = se califica mejor).

- Sin datos suficientes (hace falta que el redactor también sea juez y al menos otro juez).

## 4. ¿Se puede confiar en cada juez? (cruce)

Kappa: 1 = acuerdo total, 0 = el del azar. Spearman: 1 = ordenan igual, 0 = sin relación.

| Juez | Fidelidad vs cifras con respaldo (kappa) | Juez aprobado vs «Bien» humano (kappa) | Promedio vs humana (Spearman) | Relevancia vs humana (Spearman) | Respuestas |
|---|---|---|---|---|---|
| qwen3:4b-instruct | 0.0 (n=16) | 0.22 | 0.379 | 0.344 | 24 (24 calificadas) |

**Precisión del contexto del juez contra «contexto suficiente» (turnos de dato)**

| Juez | Alta y suficiente | Alta e insuficiente | Baja y suficiente | Baja e insuficiente |
|---|---|---|---|---|
| qwen3:4b-instruct | 14 | 1 | 0 | 0 |

## 5. ¿Falla del modelo o del código?

Un turno que sale mal con todos los redactores apunta al código (interpretación, cálculo o datos); uno que sale bien con alguno apunta al modelo. Acierto = calificación humana «Bien»; sin calificación, las métricas contra la referencia.

| Turno | Tipo | qwen3:4b-instruct | gemma3:4b | Lectura |
|---|---|---|---|---|
| 1.1 | dato | ✓ | ✓ | bien en todos |
| 1.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 1.3 | interpretativo | ✗ | ✓ | depende del modelo |
| 2.1 | capacidad | ✗ | ✗ | falla en todos: probable código |
| 2.2 | capacidad | ✗ | ✗ | falla en todos: probable código |
| 3.1 | dato | ✓ | ✓ | bien en todos |
| 3.2 | interpretativo | ✗ | ✗ | falla en todos: probable código |
| 4.1 | dato | ✓ | ✗ | depende del modelo |
| 4.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 5.1 | dato | ✗ | ✓ | depende del modelo |
| 5.2 | dato | ✗ | ✗ | falla en todos: probable código |
| 6.1 | inexistente | ✓ | ✓ | bien en todos |
| 6.2 | inexistente | ✗ | ✓ | depende del modelo |
| 7.1 | dato | ✓ | ✗ | depende del modelo |
| 8.1 | inexistente | ✓ | ✓ | bien en todos |
| 8.2 | inexistente | ✓ | ✗ | depende del modelo |
| 9.1 | dato | ✓ | ✓ | bien en todos |
| 9.2 | dato | ✓ | ✓ | bien en todos |
| 10.1 | interpretativo | ✓ | ✗ | depende del modelo |
| 10.2 | interpretativo | ✓ | ✓ | bien en todos |
| 11.1 | dato | ✗ | ✗ | falla en todos: probable código |
| 12.1 | interpretativo | ✗ | ✗ | falla en todos: probable código |