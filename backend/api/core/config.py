#archivo config.py para poder obtener las claves desde .env para FastAPI
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

#sube desde config.py hasta la raíz del proyecto
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

#esta clase va a obtener la info directamente de .env con ayuda de Pydantic

class AppSettings(BaseSettings): #esta clase va a obtener automáticamente los valores del .env
    #para la aplicación/website

    APP_NAME: str
    APP_ENV: str
    DEBUG: bool

    #para la base de datos en postgreSQL
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    #para ollama, el que nor proporciona correr los LLMs de manera local

    OLLAMA_HOST: str
    OLLAMA_MODEL: str

    #para la base de datos v en chroma db

    CHROMA_PATH: str

    #para el almacenameinto de los archivos que se generen
    RAW_PATH: str
    JSON_PATH: str
    SAV_PATH: str
    TEMP_PATH: str
    DATA_PATH: str
    #dataset limpio tras aplicar las transformaciones aprobadas (encuestas)
    CLEAN_PATH: str = "storage/clean"

    #seguridad
    SECRET_KEY: str

    #logs que mostrarán errores

    LOG_LEVEL: str

    #umbral para textos largos
    LIMPIEZA_VENTANA_CHARS: int = 1000
    #umbral para el solapamiento en los chunks, teniendo en cuenta que nuestro chunks son de 500 tokens
    LIMPIEZA_SOLAPE_CHARS: int = 150

    #intervalo del polling del pipeline de limpieza 
    LIMPIEZA_INTERVALO_SEGUNDOS: int =  30

    #la expiración del JWT debe ser configurable
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    #rediseño v2 del canónico de encuestas: reagrupar columnas en preguntas lógicas.
    #Default False = comportamiento actual. Poner SIS_QUESTION_GROUPING=true en .env
    #para probar el modo v2 sin cambiar el resto.
    SIS_QUESTION_GROUPING: bool = False

    model_config=SettingsConfigDict(
        env_file=".env",
        case_sensitive=True 
    )

    @property
    def PROJECT_ROOT(self) -> Path:
        return _PROJECT_ROOT

    @property
    def STATIC_DIR(self) -> Path:
        return _PROJECT_ROOT / "frontend" / "static"

    @property 
    def TEMPLATES_DIR(self) -> Path:
        return _PROJECT_ROOT / "frontend" / "templates"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )
    #con esta propiedad, si se llama tendremos algo como
    # postgresql1://postgres:postgres@postgres:5432/tt_rag
    #lo ocupará SQLAlquemy cuando se cree la conexión a la base de datos

    @property
    def raw_path_abs(self) -> Path:
        return _PROJECT_ROOT / self.RAW_PATH.lstrip("/")

    @property
    def json_path_abs(self) -> Path:
        return _PROJECT_ROOT /self.JSON_PATH.lstrip("/")

    @property
    def sav_path_abs(self) -> Path:
        return _PROJECT_ROOT /self.SAV_PATH.lstrip("/")

    @property
    def temp_path_abs(self) -> Path:
        return _PROJECT_ROOT /self.TEMP_PATH.lstrip("/")

    @property
    def chroma_path_abs(self) -> Path:
        return _PROJECT_ROOT / self.CHROMA_PATH.lstrip("/")

    @property 
    def data_path_abs(self) -> Path:
        return _PROJECT_ROOT / self.DATA_PATH.lstrip("/")

    @property
    def clean_path_abs(self) -> Path:
        return _PROJECT_ROOT / self.CLEAN_PATH.lstrip("/")


settings=AppSettings() #se ha creado la instancia de la clase AppSettings
