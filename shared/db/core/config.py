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
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # Usuario fijo de desarrollo (cuando no hay JWT real todavía).
    DEV_USER_ID: int = 1
    # Si es True, los servicios aceptan el usuario de desarrollo sin token.
    AUTH_DEV_MODE: bool = True

    # ── URLs de los microservicios ───────────────────────────────────────────
    INSTRUMENT_SERVICE_URL: str = "http://localhost:8001"
    ANALYSIS_SERVICE_URL: str = "http://localhost:8002"
    # Autoridad de archivos y del índice vectorial. En Docker, docker-compose.yml
    # inyecta http://storage-service:8004.
    STORAGE_SERVICE_URL: str = "http://localhost:8004"
    CLEANING_SERVICE_URL: str = "http://localhost:8007"
    KNOWLEDGE_SERVICE_URL: str = "http://localhost:8009"

    # ── metadata-service ─────────────────────────────────────────────────────
    # Si es True, la propuesta de metadatos pide a Ollama los campos que las
    # heurísticas no lograron inferir (con degradación grácil si no responde).
    METADATA_USAR_LLM: bool = True
    METADATA_LLM_TIMEOUT: float = 60.0

    # ── Búsqueda semántica de KPIs ───────────────────────────────────────────
    KPI_SEARCH_TOP_K: int = 5
    KPI_SEARCH_MIN_SCORE: float = 0.30

    # ── Asociación de KPIs por unidades del perfil semántico (analysis-service) ──
    # score = PESO_GENERAL·g + PESO_PREGUNTAS·p + PESO_COBERTURA·c, donde g es la
    # similitud perfil general↔KPI, p la media de las 3 preguntas más parecidas y
    # c = min(1, preguntas con similitud ≥ UMBRAL_EVIDENCIA / 3).
    KPI_PESO_GENERAL: float = 0.45
    KPI_PESO_PREGUNTAS: float = 0.45
    KPI_PESO_COBERTURA: float = 0.10
    KPI_UMBRAL_EVIDENCIA: float = 0.45  # calibrado con instrumentos reales (scripts/comparar_kpis.py)
    KPI_MAX_PROPUESTAS: int = 8
    # Justificación breve por KPI con el LLM (Ollama); si falla, plantilla determinística.
    KPI_JUSTIFICAR_LLM: bool = True
    KPI_LLM_TIMEOUT: float = 30.0

    # ── Chat RAG ─────────────────────────────────────────────────────────────
    # Similitud coseno mínima para que un fragmento entre al contexto del LLM.
    # Si ninguno la alcanza, el chat responde que no tiene información
    # relacionada en lugar de dejar que el modelo improvise. Calibrado con 30
    # instrumentos: preguntas sin relación ≤ 0.30, relacionadas 0.60–0.77.
    RAG_MIN_SCORE: float = 0.35
    # Dominio acotado (visualization-service/services/dominio.py). Zona gris: similitud
    # en [RAG_MIN_SCORE, RAG_ZONA_GRIS_MAX) sin que una regla decida; ahí un clasificador
    # con Ollama (JSON, temperatura 0) decide si la pregunta es del dominio. Medido en la
    # auditoría: «poema sobre motivación» 0.58, «nombre de R0017» 0.48 (los resuelven las
    # reglas), preguntas del acervo 0.60–0.70.
    RAG_ZONA_GRIS_MAX: float = 0.50
    # Sin fragmentos y con similitud máxima (acervo, glosario, ayuda y KPIs) por debajo
    # de esto, la pregunta es ajena al dominio y recibe el mensaje de «fuera» con
    # ejemplos; entre este valor y RAG_MIN_SCORE, el de «sin información». Auditoría:
    # «¿quién ganó el mundial?» 0.25; preguntas sin relación ≤ 0.30.
    RAG_FUERA_MAX: float = 0.30
    RAG_CLASIFICADOR_LLM: bool = True
    RAG_CLASIFICADOR_MODELO: str = ""  # vacío = OLLAMA_MODEL

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
