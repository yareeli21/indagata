"""Config de pytest para metadata-service.

Inserta en `sys.path`:
  - la raíz del servicio (`services/metadata-service`), para que `import main`,
    `import routers...` y `import services...` resuelvan desde cualquier cwd.
  - la raíz del repo, para que `import shared...` resuelva al correr pytest desde
    la carpeta del servicio (mismo patrón que services/analysis-service/tests/conftest.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
