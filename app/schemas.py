"""Pydantic schemas for request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from datetime import time
from zoneinfo import ZoneInfo

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from .models import ReservaStatus, UsuarioRole


TZ_AMERICA_RIO_BRANCO = ZoneInfo("America/Rio_Branco")


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2)
    email: EmailStr
    telefonewhatsapp: str = Field(min_length=8, alias="telefoneWhatsApp")
    role: UsuarioRole = UsuarioRole.Cliente

    model_config = {"populate_by_name": True}


class UsuarioOut(BaseModel):
    id: uuid.UUID
    nome: str
    email: EmailStr
    telefonewhatsapp: str = Field(alias="telefoneWhatsApp")
    role: UsuarioRole
    datacriacao: datetime = Field(alias="dataCriacao")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ReservaCreate(BaseModel):
    usuarioid: uuid.UUID = Field(alias="usuarioId")
    datareserva: date = Field(alias="dataReserva")
    horareserva: datetime = Field(alias="horaReserva")
    quantidadepessoas: int = Field(gt=0, alias="quantidadePessoas")

    model_config = {"populate_by_name": True}

    @field_validator("horareserva")
    @classmethod
    def validar_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("horaReserva deve conter fuso horário (ex: 2026-03-22T20:00:00-05:00)")
        return value

    @model_validator(mode="after")
    def validar_data_hora_consistente(self) -> "ReservaCreate":
        data_em_rio_branco = self.horareserva.astimezone(TZ_AMERICA_RIO_BRANCO).date()
        if self.datareserva != data_em_rio_branco:
            raise ValueError("dataReserva deve bater com a data de horaReserva no fuso America/Rio_Branco")
        return self


class ReservaOut(BaseModel):
    id: uuid.UUID
    usuarioid: uuid.UUID = Field(alias="usuarioId")
    datareserva: date = Field(alias="dataReserva")
    horareserva: datetime = Field(alias="horaReserva")
    quantidadepessoas: int = Field(alias="quantidadePessoas")
    status: ReservaStatus
    datacriacao: datetime = Field(alias="dataCriacao")
    dataatualizacao: datetime = Field(alias="dataAtualizacao")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ReservaStatusOut(BaseModel):
    id: uuid.UUID
    status: ReservaStatus


class ConfiguracaoHorarioOut(BaseModel):
    id: uuid.UUID
    diadasemana: int = Field(alias="diaDaSemana")
    horaabertura: time = Field(alias="horaAbertura")
    horafechamento: time = Field(alias="horaFechamento")
    capacidademaximapessoas: int = Field(alias="capacidadeMaximaPessoas")

    model_config = {"from_attributes": True, "populate_by_name": True}
