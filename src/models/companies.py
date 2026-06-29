from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from src.database.base import Base
from src.models.domains import Domain


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    dominio_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), nullable=False)
    industria: Mapped[str | None] = mapped_column(String, nullable=True)
    idioma: Mapped[str | None] = mapped_column(String, nullable=True)
    pais: Mapped[str | None] = mapped_column(String, nullable=True)

    dominio: Mapped["Domain"] = relationship(foreign_keys=[dominio_id])
