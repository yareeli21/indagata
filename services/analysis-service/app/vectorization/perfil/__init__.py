"""Asociación de KPIs desde el perfil semántico (knowledge-service).

Reemplaza, en el wizard, la propuesta basada en un solo resumen del JSON técnico:
  - `unidades`:      textos legibles (plantilla) del perfil general y de cada pregunta.
  - `asociacion`:    fórmula que agrega las similitudes por KPI, con su evidencia.
  - `justificacion`: frase breve por KPI (LLM con respaldo determinístico).
  - `servicio`:      casos de uso proponer / confirmar (lee y escribe version_conocimiento).

La colección `kpis` y su indexación NO cambian: los vectores de los KPIs solo se leen.
"""
