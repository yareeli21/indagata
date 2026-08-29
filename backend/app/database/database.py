from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


#se crea el motor, como el administrador de conexiones, prepara todo para un conexión
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

#es para cada usuario (request) que entre y tenga su propia sesión
SessionLocal=sessionmaker(
    bind=engine, 
    autoflush=False,
    autocommit=False
)
#abre la conexi+on, usa la conexión y cierra la conexión, es la dependency para FASTAPI
def get_db():
    db=SessionLocal()

    try:
        yield db 
    finally:
        db.close()