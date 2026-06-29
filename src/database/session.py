from typing import Generator
from sqlalchemy.orm import sessionmaker, Session
from src.database.connection import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Generador que provee una sesión de base de datos."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
