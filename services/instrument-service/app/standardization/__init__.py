"""Etapa de estandarización del instrument-service (diseño §1).

Detecta tipos de pregunta a partir del archivo respondido ya parseado y
construye el JSON de dominio con el esquema del seed (`storage/raw/inst_XX.v1.json`).
Es la pieza que escribe `instrumento_procesado.ruta_json` y avanza el estado a
`estandarizado`.
"""
