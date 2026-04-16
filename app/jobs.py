"""APScheduler jobs for BDP background routines."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .crud import mover_pendentes_para_aguardando_confirmacao
from .database import SessionLocal


TZ_AMERICA_RIO_BRANCO = ZoneInfo("America/Rio_Branco")


async def job_atualizar_reservas_pendentes() -> None:
    hoje = datetime.now(TZ_AMERICA_RIO_BRANCO).date()
    async with SessionLocal() as session:
        async with session.begin():
            await mover_pendentes_para_aguardando_confirmacao(session, hoje)


def configurar_scheduler(scheduler: AsyncIOScheduler) -> None:
    trigger = CronTrigger(hour=10, minute=0, timezone=TZ_AMERICA_RIO_BRANCO)
    scheduler.add_job(
        job_atualizar_reservas_pendentes,
        trigger=trigger,
        id="bdp_atualizar_pendentes",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
    )
