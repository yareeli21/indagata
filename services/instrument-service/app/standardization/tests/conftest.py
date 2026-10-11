"""Config de pytest para la etapa de estandarización del instrument-service.

Inserta en `sys.path`:
  - la raíz del servicio (`services/instrument-service`), para que `import app...`
    y `import main` resuelvan desde cualquier cwd.
  - la raíz del repo, para que `import shared...` resuelva al correr pytest desde
    la carpeta del servicio (mismo patrón que analysis-service/tests/conftest.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

# app/standardization/tests/conftest.py -> parents[3] = services/instrument-service
_SERVICE_ROOT = Path(__file__).resolve().parents[3]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

# parents[5] = raíz del repo (indagata/)
_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
