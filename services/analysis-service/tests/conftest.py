"""Config de pytest para analysis-service.

Inserta la raíz del servicio (`services/analysis-service`) en `sys.path` para
que `import scripts.seed_kpis` resuelva al ejecutar los tests desde cualquier
cwd, y la raíz del repo para que `app.*` encuentre el paquete `shared`.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
_REPO = _SERVICE_ROOT.parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))
if (_REPO / "shared").is_dir() and str(_REPO) not in sys.path:
    sys.path.insert(1, str(_REPO))
