from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

<<<<<<<< HEAD:backend/db/database.py
from app.core.config import settings
from sqlalchemy.ext.declarative import declarative_base
========
from api.core.config import settings
>>>>>>>> f1c3938aeebc5033b4cb855099078e64d6803376:backend/api/database/database.py


#se crea el motor, como el administrador de conexiones, prepara todo para un conexión
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,  # descarta conexiones muertas antes de usarlas (robustez ante timeouts de red/BD)
)

#es para cada usuario (request) que entre y tenga su propia sesión
SessionLocal=sessionmaker(
    bind=engine, 
    autoflush=False,
    autocommit=False
)
Base = declarative_base()
#abre la conexi+on, usa la conexión y cierra la conexión, es la dependency para FASTAPI
def get_db():
    db=SessionLocal()

    try:
        yield db 
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)