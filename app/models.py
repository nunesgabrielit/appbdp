"""SQLAlchemy models for the BDP schema.

These models map to the tables created by database/01_init_schema.sql.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text


class Base(DeclarativeBase):
    pass


class UsuarioRole(str, enum.Enum):
    Cliente = "Cliente"
    Admin = "Admin"


class ReservaStatus(str, enum.Enum):
    Pendente = "Pendente"
    Aguardando_Confirmacao = "Aguardando_Confirmacao"
    Confirmado = "Confirmado"
    Cancelado = "Cancelado"
    Concluido = "Concluido"
    No_Show = "No_Show"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    nome: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    telefonewhatsapp: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UsuarioRole] = mapped_column(
        Enum(UsuarioRole, name="usuario_role", create_type=False),
        nullable=False,
        server_default=text("'Cliente'"),
    )
    datacriacao: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    reservas: Mapped[list["Reserva"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ConfiguracaoHorario(Base):
    __tablename__ = "configuracao_horarios"
    __table_args__ = (
        CheckConstraint("diadasemana BETWEEN 1 AND 7", name="configuracao_horarios_diadasemana_ck"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    diadasemana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    horaabertura: Mapped[object] = mapped_column(Time, nullable=False)
    horafechamento: Mapped[object] = mapped_column(Time, nullable=False)
    capacidademaximapessoas: Mapped[int] = mapped_column(Integer, nullable=False)


class Reserva(Base):
    __tablename__ = "reservas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    usuarioid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    datareserva: Mapped[object] = mapped_column(Date, nullable=False)
    horareserva: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    quantidadepessoas: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservaStatus] = mapped_column(
        Enum(ReservaStatus, name="reserva_status", create_type=False),
        nullable=False,
        server_default=text("'Pendente'"),
    )
    datacriacao: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    dataatualizacao: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    usuario: Mapped[Usuario] = relationship(back_populates="reservas")
