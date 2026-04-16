import asyncio
from pathlib import Path

import pytest

from app.startup import StartupConfig, _mask_database_url, compute_missing_requirements, ensure_dependencies


def test_mask_database_url():
    assert _mask_database_url("postgresql+asyncpg://user:pass@localhost:5432/db") == "postgresql+asyncpg://user:***@localhost:5432/db"


def test_compute_missing_requirements_marks_missing(monkeypatch):
    from app import startup

    def fake_version(name: str) -> str:
        raise startup.metadata.PackageNotFoundError

    monkeypatch.setattr(startup.metadata, "version", fake_version)
    missing = compute_missing_requirements(["fastapi>=0.110"])
    assert missing == ["fastapi>=0.110"]


def test_ensure_dependencies_skips_when_nothing_missing(tmp_path, monkeypatch, capsys):
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("fastapi>=0.110\n", encoding="utf-8")

    from app import startup

    monkeypatch.setattr(startup, "compute_missing_requirements", lambda reqs: [])
    ensure_dependencies(requirements_path, startup._configure_logging())
    out = capsys.readouterr().out
    assert "Dependências já estão instaladas" in out


@pytest.mark.asyncio
async def test_validate_database_connection_success(monkeypatch):
    from app import startup

    class FakeConn:
        async def execute(self, _sql: str):
            return None

        async def close(self):
            return None

    async def fake_connect(_dsn: str):
        return FakeConn()

    import asyncpg

    monkeypatch.setattr(asyncpg, "connect", fake_connect)
    await startup.validate_database_connection("postgresql://user:pass@localhost:5432/db", startup._configure_logging())
