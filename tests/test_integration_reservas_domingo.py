import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


TZ_AMERICA_RIO_BRANCO = ZoneInfo("America/Rio_Branco")


@pytest.mark.asyncio
async def test_post_reservas_domingo_usa_dia_7(client):
    hoje = datetime.now(TZ_AMERICA_RIO_BRANCO).date()
    delta = (7 - hoje.isoweekday()) % 7
    data_domingo = hoje + timedelta(days=delta)

    hora_reserva = datetime(
        data_domingo.year,
        data_domingo.month,
        data_domingo.day,
        20,
        0,
        0,
        tzinfo=TZ_AMERICA_RIO_BRANCO,
    )

    payload_usuario = {
        "nome": "Cliente Teste Domingo",
        "email": f"cliente_domingo_{uuid.uuid4().hex}@bdp.com",
        "telefoneWhatsApp": "+55999999999",
        "role": "Cliente",
    }
    resp_user = await client.post("/usuarios", json=payload_usuario)
    assert resp_user.status_code == 201, resp_user.text
    usuario_id = resp_user.json()["id"]

    payload_reserva = {
        "usuarioId": usuario_id,
        "dataReserva": data_domingo.isoformat(),
        "horaReserva": hora_reserva.isoformat(),
        "quantidadePessoas": 2,
    }
    resp = await client.post("/reservas", json=payload_reserva)
    assert resp.status_code == 201, resp.text
