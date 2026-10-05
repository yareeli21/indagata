from sqlalchemy.orm import declarative_base
from sqlmodel import create_engine, Session
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel 

import os
from dotenv import load_dotenv


#ARCHIVO LAYYYYY NO BORRAR PORFA ES PARA LA BASE DE DATOS

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "indagata_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

URL_BASE = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(URL_BASE, echo=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base

def get_db():

    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    SQLModel.metadata.create_all(engine)