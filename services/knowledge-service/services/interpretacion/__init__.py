"""Capa de interpretación de respuestas: convierte cada valor crudo en datos con significado.

Cada respuesta interpretada tiene, según el caso:
  - estado:              respondida | sin_respuesta | no_interpretada   (pruebas: valida | nula | sin_respuesta)
  - valor:               el valor original (código, número o texto)
  - significado:         la etiqueta exacta («En desacuerdo», «Sí», «Opción C»…)
  - nivel:               agrupación para consultas («desacuerdo» / «neutral» / «acuerdo»…)
  - valor_recodificado:  solo ítems Likert invertidos (lo + hi − x)
  - seleccion:           opción múltiple y ranking (lista)
  - texto:               respuestas abiertas, tal cual
  - motivo:              por qué no hay respuesta válida (si se sabe)

Todo es DETERMINÍSTICO (plantillas y diccionarios); nunca se usa el LLM aquí. Lo que no
se puede interpretar se marca `no_interpretada` y genera un aviso; nada se omite ni se
inventa (las respuestas faltantes quedan como `sin_respuesta`).

Módulos:
  - config:    reglas editables (`config/conocimiento.yaml`) y escalas (`shared/config`).
  - escalas:   niveles por posición de cada escala.
  - privacidad: columnas con datos personales (palabra completa).
  - encuestas: intérpretes por tipo canónico de pregunta.
  - pruebas:   respuestas de pruebas estandarizadas.
"""
