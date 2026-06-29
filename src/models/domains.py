from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from src.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dominio: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    fecha_descubrimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    fuente: Mapped[str] = mapped_column(String, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
