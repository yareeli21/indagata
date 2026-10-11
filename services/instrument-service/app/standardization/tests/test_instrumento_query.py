"""Bug 5: _slug_por_id_crudo ya NO cae al patrón directo inst_{N:02d}."""
from __future__ import annotations

from app.services import instrumento_query as iq


def test_sin_seed_map_devuelve_none(monkeypatch):
    # Sin _seed_map.json el mapa está vacío -> sin mapeo -> None (sin fallback).
    monkeypatch.setattr(iq, "_cargar_seed_map", lambda: {})
    assert iq._slug_por_id_crudo(1) is None
    assert iq._slug_por_id_crudo(11) is None


def test_con_seed_map_devuelve_slug(monkeypatch):
    monkeypatch.setattr(iq, "_cargar_seed_map", lambda: {"inst_01": 1, "inst_03": 7})
    assert iq._slug_por_id_crudo(1) == "inst_01"
    assert iq._slug_por_id_crudo(7) == "inst_03"
    # id_crudo sin mapeo explícito -> None (no inst_02).
    assert iq._slug_por_id_crudo(2) is None
