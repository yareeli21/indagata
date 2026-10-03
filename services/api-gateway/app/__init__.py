"""API Gateway — aplicación.

Incluye el módulo de AUTENTICACIÓN (app/auth): login por email+password, emisión
de JWT firmado, consulta del usuario actual y alta de usuarios (solo administrador).
Los demás microservicios validan ese JWT con la misma SECRET_KEY compartida.
"""
