"""Roles del sistema (vocabulario cerrado).

Alineado con la columna `usuario.rol`. Dos roles:
  - investigador:  puede ingestar instrumentos y eliminar los suyos.
  - administrador: acceso total (ingesta, borrado de cualquiera, alta de usuarios).
"""
from __future__ import annotations

ROL_INVESTIGADOR = "investigador"
ROL_ADMINISTRADOR = "administrador"

ROLES_VALIDOS: frozenset[str] = frozenset({ROL_INVESTIGADOR, ROL_ADMINISTRADOR})

# Rol técnico de las llamadas servicio→servicio (p. ej. metadata-service →
# storage-service). NO es un rol de usuario: no se puede asignar en el alta y
# por eso no forma parte de ROLES_VALIDOS. Ver shared/auth/servicio.py.
ROL_SERVICIO = "servicio"
