from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey, DateTime
from src.database.base import Base
from src.models.companies import Company


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    estado: Mapped[str] = mapped_column(String, nullable=False, default="new")
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped["Company"] = relationship(foreign_keys=[company_id])
