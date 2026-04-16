"""Database access helpers for the BDP API."""

from __future__ import annotations

import uuid
from datetime import date, time
from zoneinfo import ZoneInfo

from sqlalchemy import Time, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ConfiguracaoHorario, Reserva, ReservaStatus, Usuario


TZ_AMERICA_RIO_BRANCO = ZoneInfo("America/Rio_Branco")
TZNAME_AMERICA_RIO_BRANCO = "America/Rio_Branco"
RESERVA_STATUS_ATIVOS: tuple[ReservaStatus, ...] = (
    ReservaStatus.Pendente,
    ReservaStatus.Aguardando_Confirmacao,
    ReservaStatus.Confirmado,
)


def _hora_local_rio_branco(hora_reserva) -> time:
    return hora_reserva.astimezone(TZ_AMERICA_RIO_BRANCO).time().replace(tzinfo=None)


async def criar_usuario(session: AsyncSession, *, nome: str, email: str, telefonewhatsapp: str, role) -> Usuario:
    usuario = Usuario(
        nome=nome.strip(),
        email=str(email).strip(),
        telefonewhatsapp=telefonewhatsapp.strip(),
        role=role,
    )
    session.add(usuario)
    await session.flush()
    return usuario


async def buscar_usuario_por_id(session: AsyncSession, usuario_id: uuid.UUID) -> Usuario | None:
    result = await session.execute(select(Usuario).where(Usuario.id == usuario_id))
    return result.scalar_one_or_none()


async def listar_usuarios(session: AsyncSession) -> list[Usuario]:
    result = await session.execute(select(Usuario).order_by(Usuario.nome.asc(), Usuario.datacriacao.asc()))
    return list(result.scalars().all())


async def listar_configuracoes_horario(session: AsyncSession) -> list[ConfiguracaoHorario]:
    result = await session.execute(
        select(ConfiguracaoHorario).order_by(
            ConfiguracaoHorario.diadasemana.asc(),
            ConfiguracaoHorario.horaabertura.asc(),
        )
    )
    return list(result.scalars().all())


async def obter_capacidade_para_reserva(
    session: AsyncSession,
    *,
    data_reserva: date,
    hora_reserva,
) -> int | None:
    dia = data_reserva.isoweekday()
    hora_local = _hora_local_rio_branco(hora_reserva)

    stmt = (
        select(ConfiguracaoHorario.capacidademaximapessoas)
        .where(ConfiguracaoHorario.diadasemana == dia)
        .where(hora_local >= ConfiguracaoHorario.horaabertura)
        .where(hora_local < ConfiguracaoHorario.horafechamento)
        .order_by(ConfiguracaoHorario.horaabertura.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def usuario_tem_reserva_ativa_no_dia(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    data_reserva: date,
) -> bool:
    stmt = (
        select(func.count())
        .select_from(Reserva)
        .where(Reserva.usuarioid == usuario_id)
        .where(Reserva.datareserva == data_reserva)
        .where(Reserva.status.in_(RESERVA_STATUS_ATIVOS))
    )
    result = await session.execute(stmt)
    return (result.scalar_one() or 0) > 0


async def obter_total_pessoas_no_horario(
    session: AsyncSession,
    *,
    data_reserva: date,
    hora_reserva,
) -> int:
    hora_local = _hora_local_rio_branco(hora_reserva)
    hora_local_expr = cast(func.timezone(TZNAME_AMERICA_RIO_BRANCO, Reserva.horareserva), Time)

    stmt = (
        select(func.coalesce(func.sum(Reserva.quantidadepessoas), 0))
        .where(Reserva.datareserva == data_reserva)
        .where(Reserva.status.in_(RESERVA_STATUS_ATIVOS))
        .where(hora_local_expr == hora_local)
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def criar_reserva(
    session: AsyncSession,
    *,
    usuario_id: uuid.UUID,
    data_reserva: date,
    hora_reserva,
    quantidade_pessoas: int,
) -> Reserva:
    reserva = Reserva(
        usuarioid=usuario_id,
        datareserva=data_reserva,
        horareserva=hora_reserva,
        quantidadepessoas=quantidade_pessoas,
        status=ReservaStatus.Pendente,
    )
    session.add(reserva)
    await session.flush()
    return reserva


async def listar_reservas_por_data(session: AsyncSession, data_reserva: date) -> list[Reserva]:
    result = await session.execute(select(Reserva).where(Reserva.datareserva == data_reserva).order_by(Reserva.horareserva))
    return list(result.scalars().all())


async def atualizar_status_reserva(
    session: AsyncSession,
    *,
    reserva_id: uuid.UUID,
    status: ReservaStatus,
) -> Reserva | None:
    result = await session.execute(select(Reserva).where(Reserva.id == reserva_id))
    reserva = result.scalar_one_or_none()
    if not reserva:
        return None
    reserva.status = status
    await session.flush()
    return reserva


async def mover_pendentes_para_aguardando_confirmacao(session: AsyncSession, data_reserva: date) -> int:
    stmt = (
        update(Reserva)
        .where(Reserva.datareserva == data_reserva)
        .where(Reserva.status == ReservaStatus.Pendente)
        .values(status=ReservaStatus.Aguardando_Confirmacao)
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)
