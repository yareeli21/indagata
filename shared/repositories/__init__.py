"""Capa de repositorios compartida.

Los repositorios previos se eliminaron por quedar desalineados con
`infrastructure/postgres/init/01_schema.sql` (dependían de DTOs o columnas
inexistentes). Los servicios que necesiten helpers de persistencia deben
definirlos contra los modelos realineados en `shared.models`.
"""
