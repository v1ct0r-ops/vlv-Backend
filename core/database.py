import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Obtener URL del .env o usar default según el ambiente
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gas_user:gas_password_secreta@db:5432/gas_db"
)

print(f" Base de datos: {DATABASE_URL}")

# sqlite se usa solo en los tests; postgres es la base real
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()