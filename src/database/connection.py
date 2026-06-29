from sqlalchemy import create_engine, Engine
from src.config.settings import settings


def get_engine(database_url: str = settings.DATABASE_URL) -> Engine:
    """Crea y retorna un SQLAlchemy Engine."""
    # check_same_thread=False is needed for SQLite if accessed from multiple threads
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args)


engine = get_engine()
