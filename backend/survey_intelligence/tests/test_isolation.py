# survey_intelligence/tests/test_isolation.py
"""
Test de aislamiento (design.md §1, requisito 1.2 / 13.5).

Verifica que el núcleo del SIS NO importe nada del host (api, services, FastAPI,
SQLAlchemy). Si algún módulo del componente introduce un import prohibido, este
test falla.

Ejecutar:
    python -m survey_intelligence.tests.test_isolation
"""
from __future__ import annotations

import ast
import pathlib

# Raíz del componente (survey_intelligence/)
_COMPONENT_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Prefijos de import prohibidos dentro del núcleo del SIS.
_FORBIDDEN_PREFIXES = ("api", "services", "fastapi", "sqlalchemy", "starlette")


def _iter_module_files() -> list[pathlib.Path]:
    """Todos los .py del componente excepto la carpeta de tests."""
    return [
        p
        for p in _COMPONENT_ROOT.rglob("*.py")
        if "tests" not in p.relative_to(_COMPONENT_ROOT).parts
    ]


def _imported_roots(source: str) -> set[str]:
    """Extrae el primer segmento de cada import del archivo."""
    roots: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:  # ignora imports relativos
                roots.add(node.module.split(".")[0])
    return roots


def test_core_does_not_import_host_modules() -> None:
    """Ningún módulo del componente debe importar prefijos prohibidos del host."""
    violations: list[str] = []
    for path in _iter_module_files():
        roots = _imported_roots(path.read_text(encoding="utf-8"))
        bad = roots.intersection(_FORBIDDEN_PREFIXES)
        if bad:
            rel = path.relative_to(_COMPONENT_ROOT)
            violations.append(f"{rel}: importa {sorted(bad)}")

    assert not violations, (
        "El núcleo del SIS no debe importar módulos del host:\n"
        + "\n".join(violations)
    )


def test_ports_defaults_operate_without_infrastructure() -> None:
    """Las implementaciones por defecto funcionan sin infraestructura externa."""
    from survey_intelligence.ports import (
        NullTelemetry,
        SystemClock,
        UuidGenerator,
    )

    NullTelemetry().event("sis.stage.test", {"k": "v"})

    assert SystemClock().now() is not None

    ids = UuidGenerator()
    first = ids.new_id("prop-")
    assert first.startswith("prop-")
    assert first != ids.new_id("prop-")


def _run() -> None:
    test_core_does_not_import_host_modules()
    test_ports_defaults_operate_without_infrastructure()
    print("OK - test_isolation: 2 tests passed")


if __name__ == "__main__":
    _run()
