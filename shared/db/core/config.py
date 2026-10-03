"""Configuración central (settings) leída desde variables de entorno / .env.

Compartida por todos los microservicios. Usa pydantic-settings. Todos los
campos tienen un valor por defecto razonable para que un servicio pueda
arrancar en desarrollo aunque falte parte del .env; en producción (Docker)
las variables llegan por el entorno del contenedor.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# shared/db/core/config.py -> parents[3] = raíz del repo (indagata/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AppSettings(BaseSettings):
    """Configuración de la aplicación. Lee del entorno y de un archivo .env."""

    # ── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "Indagata"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Base de datos PostgreSQL ─────────────────────────────────────────────
    POSTGRES_DB: str = "indagata_db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ── Ollama (LLM local) ───────────────────────────────────────────────────
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # ── ChromaDB (vector store) ──────────────────────────────────────────────
    CHROMA_PATH: str = "chromadb/data"
    # Conexión al servidor Chroma (contenedor). En local apunta a localhost; en
    # Docker, docker-compose.yml inyecta CHROMA_HOST=chromadb.
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8008
    # Modelo de embeddings multilingüe (sentence-transformers). 768 dimensiones.
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    # Colecciones de ChromaDB.
    CHROMA_COLLECTION_INSTRUMENTOS: str = "instrumentos"
    CHROMA_COLLECTION_KPIS: str = "kpis"
    # Colección del resumen del instrumento (original + metadatos clave) para la
    # búsqueda semántica de KPIs.
    CHROMA_COLLECTION_SUMMARY: str = "summary_instrument"

    # ── Almacenamiento de archivos ───────────────────────────────────────────
    RAW_PATH: str = "storage/raw"
    JSON_PATH: str = "storage/json"
    SAV_PATH: str = "storage/sav"
    CLEAN_PATH: str = "storage/clean"
    TEMP_PATH: str = "storage/temp"

    # ── Seguridad / JWT ──────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Usuario fijo de desarrollo (cuando no hay JWT real todavía).
    DEV_USER_ID: int = 1
    # Si es True, los servicios aceptan el usuario de desarrollo sin token.
    AUTH_DEV_MODE: bool = True

    # ── URLs de los microservicios ───────────────────────────────────────────
    INSTRUMENT_SERVICE_URL: str = "http://localhost:8001"
    ANALYSIS_SERVICE_URL: str = "http://localhost:8002"

    # ── Búsqueda semántica de KPIs ───────────────────────────────────────────
    KPI_SEARCH_TOP_K: int = 5
    KPI_SEARCH_MIN_SCORE: float = 0.30

    model_config = SettingsConfigDict(
        # Ruta absoluta al .env de la raíz del repo, para que se encuentre sin
        # importar desde qué carpeta se arranque el servicio (local o Docker).
        env_file=(str(_PROJECT_ROOT / ".env"), ".env"),
        case_sensitive=True,
        extra="ignore",
    )

    # ── Rutas derivadas (absolutas desde la raíz del repo) ───────────────────
    @property
    def PROJECT_ROOT(self) -> Path:
        return _PROJECT_ROOT

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    def _abs(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else _PROJECT_ROOT / rel.lstrip("/\\")

    @property
    def raw_path_abs(self) -> Path:
        return self._abs(self.RAW_PATH)

    @property
    def json_path_abs(self) -> Path:
        return self._abs(self.JSON_PATH)

    @property
    def sav_path_abs(self) -> Path:
        return self._abs(self.SAV_PATH)

    @property
    def clean_path_abs(self) -> Path:
        return self._abs(self.CLEAN_PATH)

    @property
    def temp_path_abs(self) -> Path:
        return self._abs(self.TEMP_PATH)

    @property
    def chroma_path_abs(self) -> Path:
        return self._abs(self.CHROMA_PATH)


settings = AppSettings()
