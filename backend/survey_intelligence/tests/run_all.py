# survey_intelligence/tests/run_all.py
"""
Runner de toda la suite de tests del SIS.

Ejecuta cada módulo de test y falla (exit 1) si alguno falla. Sirve como guardián
del build sin necesitar pytest.

Ejecutar:
    python -m survey_intelligence.tests.run_all
"""
from __future__ import annotations

import importlib
import sys

_MODULES = [
    "test_isolation",
    "test_ingestion",
    "test_canonical",
    "test_profiling",
    "test_context_sufficiency",
    "test_column_proposals",
    "test_transforms",
    "test_spss_mapper",
    "test_llm_stages",
    "test_codebook_resolution",
    "test_kpi_inference",
    "test_gap_analysis",
    "test_results_analysis",
    "test_facade",
    "test_sav_writer",
    "test_document_path",
    "test_critical_invariants",
    "test_question_grouping",
]


def main() -> int:
    failed: list[str] = []
    for name in _MODULES:
        mod = importlib.import_module(f"survey_intelligence.tests.{name}")
        try:
            mod._run()  # cada módulo expone _run()
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{name}: {exc}")
            print(f"FAIL - {name}: {exc}")

    if failed:
        print(f"\n{len(failed)} módulo(s) fallaron.")
        return 1
    print("\nTODOS los tests del SIS pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
