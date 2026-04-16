"""BDP REST API (FastAPI + SQLAlchemy async + PostgreSQL + APScheduler)."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from .database import get_session
from .jobs import configurar_scheduler
from .models import ReservaStatus
from .schemas import (
    ConfiguracaoHorarioOut,
    ReservaCreate,
    ReservaOut,
    ReservaStatusOut,
    UsuarioCreate,
    UsuarioOut,
)


TZ_AMERICA_RIO_BRANCO = ZoneInfo("America/Rio_Branco")
DEFAULT_ADMIN_ACCESS_KEY = "gabriel15"


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone=TZ_AMERICA_RIO_BRANCO)
    configurar_scheduler(scheduler)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="BDP API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin_access(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    expected_key = os.getenv("ADMIN_ACCESS_KEY", DEFAULT_ADMIN_ACCESS_KEY)
    if not x_admin_key or x_admin_key != expected_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso administrativo negado")


@app.post("/usuarios", response_model=UsuarioOut, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
async def criar_usuario(payload: UsuarioCreate, session: AsyncSession = Depends(get_session)) -> UsuarioOut:
    try:
        async with session.begin():
            usuario = await crud.criar_usuario(
                session,
                nome=payload.nome,
                email=str(payload.email),
                telefonewhatsapp=payload.telefonewhatsapp,
                role=payload.role,
            )
        return UsuarioOut.model_validate(usuario)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado") from None


@app.get("/usuarios", response_model=list[UsuarioOut], response_model_by_alias=True)
async def listar_usuarios(
    _admin: None = Depends(require_admin_access),
    session: AsyncSession = Depends(get_session),
) -> list[UsuarioOut]:
    usuarios = await crud.listar_usuarios(session)
    return [UsuarioOut.model_validate(usuario) for usuario in usuarios]


@app.get("/configuracoes-horarios", response_model=list[ConfiguracaoHorarioOut], response_model_by_alias=True)
async def listar_configuracoes_horarios(session: AsyncSession = Depends(get_session)) -> list[ConfiguracaoHorarioOut]:
    configuracoes = await crud.listar_configuracoes_horario(session)
    return [ConfiguracaoHorarioOut.model_validate(configuracao) for configuracao in configuracoes]


@app.post("/reservas", response_model=ReservaOut, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
async def criar_reserva(payload: ReservaCreate, session: AsyncSession = Depends(get_session)) -> ReservaOut:
    try:
        async with session.begin():
            usuario = await crud.buscar_usuario_por_id(session, payload.usuarioid)
            if not usuario:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

            if await crud.usuario_tem_reserva_ativa_no_dia(session, usuario_id=payload.usuarioid, data_reserva=payload.datareserva):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Usuario ja possui uma reserva ativa nesta data",
                )

            capacidade = await crud.obter_capacidade_para_reserva(
                session,
                data_reserva=payload.datareserva,
                hora_reserva=payload.horareserva,
            )
            if capacidade is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nao existe configuracao de horario para esta data/horario",
                )

            total_atual = await crud.obter_total_pessoas_no_horario(
                session,
                data_reserva=payload.datareserva,
                hora_reserva=payload.horareserva,
            )
            if total_atual + payload.quantidadepessoas > capacidade:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Capacidade maxima do horario atingida")

            reserva = await crud.criar_reserva(
                session,
                usuario_id=payload.usuarioid,
                data_reserva=payload.datareserva,
                hora_reserva=payload.horareserva,
                quantidade_pessoas=payload.quantidadepessoas,
            )
        return ReservaOut.model_validate(reserva)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Regra de reserva ativa por dia violada",
        ) from None


@app.get("/reservas/hoje", response_model=list[ReservaOut], response_model_by_alias=True)
async def listar_reservas_hoje(
    _admin: None = Depends(require_admin_access),
    session: AsyncSession = Depends(get_session),
) -> list[ReservaOut]:
    hoje = datetime.now(TZ_AMERICA_RIO_BRANCO).date()
    reservas = await crud.listar_reservas_por_data(session, hoje)
    return [ReservaOut.model_validate(r) for r in reservas]


@app.get("/reservas", response_model=list[ReservaOut], response_model_by_alias=True)
async def listar_reservas_por_data(
    data_reserva: date = Query(..., alias="data"),
    _admin: None = Depends(require_admin_access),
    session: AsyncSession = Depends(get_session),
) -> list[ReservaOut]:
    reservas = await crud.listar_reservas_por_data(session, data_reserva)
    return [ReservaOut.model_validate(r) for r in reservas]


@app.put("/reservas/{reserva_id}/cancelar", response_model=ReservaStatusOut, response_model_by_alias=True)
async def cancelar_reserva(
    reserva_id: uuid.UUID = Path(...),
    _admin: None = Depends(require_admin_access),
    session: AsyncSession = Depends(get_session),
) -> ReservaStatusOut:
    async with session.begin():
        reserva = await crud.atualizar_status_reserva(session, reserva_id=reserva_id, status=ReservaStatus.Cancelado)
        if not reserva:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva nao encontrada")
    return ReservaStatusOut(id=reserva.id, status=reserva.status)


@app.put("/reservas/{reserva_id}/confirmar", response_model=ReservaStatusOut, response_model_by_alias=True)
async def confirmar_reserva(
    reserva_id: uuid.UUID = Path(...),
    _admin: None = Depends(require_admin_access),
    session: AsyncSession = Depends(get_session),
) -> ReservaStatusOut:
    async with session.begin():
        reserva = await crud.atualizar_status_reserva(session, reserva_id=reserva_id, status=ReservaStatus.Confirmado)
        if not reserva:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva nao encontrada")
    return ReservaStatusOut(id=reserva.id, status=reserva.status)
