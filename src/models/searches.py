from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime
from src.database.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    keyword: Mapped[str] = mapped_column(String, nullable=False)
    idioma: Mapped[str] = mapped_column(String, nullable=False)
    pais: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
