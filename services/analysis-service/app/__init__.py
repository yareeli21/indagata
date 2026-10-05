"""Analysis Service — aplicación.

Incluye el módulo de VECTORIZACIÓN e inferencia de KPIs (app/vectorization):
recibe el JSON del instrumento (metadatos + respuestas) y el instrumento original
(.md adjunto), vectoriza solo lo clave (original + metadatos) en Chroma, busca los
KPIs más cercanos por similitud semántica, los propone al usuario y, al confirmar,
enriquece el JSON con los KPIs aceptados.
"""
