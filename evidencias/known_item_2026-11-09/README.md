# Búsqueda de elemento conocido (9 nov 2026)

Cada pregunta o reactivo de los instrumentos 127, 130, 129, 61 y 60 (84 en total) se usó como consulta, y se midió en
qué lugar devuelve la búsqueda un fragmento de esa misma pregunta. Script: `tools/rag/known_item.py` (modelo de
embeddings, colección y filtro del chat; 8 fragmentos por consulta; sin modelo de lenguaje).

- `consultas.json`: las 84 consultas, en dos variantes (texto completo y solo palabras con contenido).
- `resultado.json`: hit@1, @3, @5, @8 y MRR por tipo e instrumento, y las consultas cuyo fragmento no quedó primero.

Resultado: hit@1 0.976, hit@3 1.00, MRR 0.988 en las dos variantes. Las 4 consultas que no quedaron primero quedaron
segundas: dos detrás del chunk de un KPI y dos por dos preguntas casi iguales de la encuesta 61 (horas de estudio en
número y en rangos).
