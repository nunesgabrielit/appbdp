from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True)
class StartupConfig:
    database_url: str
    requirements_path: Path
    schema_path: Path | None = None
    app_import: str = "app.main:app"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True


def _mask_database_url(database_url: str) -> str:
    if not database_url:
        return ""
    return re.sub(r"//([^:/]+):([^@]+)@", r"//\1:***@", database_url)


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger("bdp_startup")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    file_handler = logging.FileHandler("bdp_startup.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def _normalize_asyncpg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + database_url.removeprefix("postgresql+asyncpg://")
    return database_url


def _maintenance_database_url(database_url: str, maintenance_db: str = "postgres") -> str:
    parsed = urlparse(_normalize_asyncpg_dsn(database_url))
    if parsed.scheme not in {"postgresql", "postgres"}:
        return _normalize_asyncpg_dsn(database_url)
    new_path = "/" + maintenance_db
    return urlunparse(parsed._replace(path=new_path))


def _database_name_from_url(database_url: str) -> str:
    parsed = urlparse(_normalize_asyncpg_dsn(database_url))
    db_name = (parsed.path or "").lstrip("/")
    if not db_name:
        raise RuntimeError("DATABASE_URL inválida: falta o nome do banco no final (ex: ...:5432/bdp_app)")
    return db_name


def _quote_ident(identifier: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise RuntimeError(f"Nome de database inválido para criação automática: {identifier!r}")
    return f'"{identifier}"'


def _try_import_packaging():
    try:
        from packaging.requirements import Requirement  # type: ignore
        from packaging.specifiers import SpecifierSet  # type: ignore
    except Exception:
        return None
    return Requirement, SpecifierSet


def _dist_satisfies(dist_name: str, spec) -> bool:
    try:
        version = metadata.version(dist_name)
    except metadata.PackageNotFoundError:
        return False
    return version in spec


def compute_missing_requirements(requirements: Iterable[str]) -> list[str]:
    packaging = _try_import_packaging()
    if not packaging:
        return list(requirements)
    Requirement, SpecifierSet = packaging

    missing: list[str] = []
    for raw in requirements:
        req = Requirement(raw)
        name = req.name
        spec = req.specifier or SpecifierSet()
        if not _dist_satisfies(name, spec):
            missing.append(raw)
    return missing


def ensure_dependencies(requirements_path: Path, logger: logging.Logger) -> None:
    requirements = [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    missing = compute_missing_requirements(requirements)
    if not missing:
        logger.info("Dependências já estão instaladas.")
        return

    logger.info("Instalando dependências faltantes: %s", ", ".join(missing))
    cmd = [sys.executable, "-m", "pip", "install", *missing]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        logger.info("Tentando instalação completa do requirements.txt")
        result_full = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            check=False,
        )
        if result_full.returncode != 0:
            raise RuntimeError(
                "Falha ao instalar dependências. Execute manualmente: python -m pip install -r requirements.txt"
            )


async def validate_database_connection(database_url: str, logger: logging.Logger) -> None:
    try:
        import asyncpg  # type: ignore
    except Exception as exc:
        raise RuntimeError("Dependência asyncpg não encontrada. Rode: python -m pip install -r requirements.txt") from exc

    try:
        conn = await asyncpg.connect(_normalize_asyncpg_dsn(database_url))
    except Exception as exc:
        masked = _mask_database_url(database_url)
        raise RuntimeError(
            "Falha ao conectar no PostgreSQL usando DATABASE_URL. "
            f"Valor (mascarado): {masked}. "
            "Verifique se o Postgres está rodando e se usuário/senha/banco estão corretos."
        ) from exc

    try:
        await conn.execute("SELECT 1;")
    finally:
        await conn.close()

    logger.info("Conexão com PostgreSQL validada com sucesso.")


async def ensure_database_exists(database_url: str, logger: logging.Logger) -> None:
    try:
        import asyncpg  # type: ignore
    except Exception as exc:
        raise RuntimeError("Dependência asyncpg não encontrada. Rode: python -m pip install -r requirements.txt") from exc

    db_name = _database_name_from_url(database_url)
    maintenance_url = _maintenance_database_url(database_url, "postgres")

    conn = await asyncpg.connect(maintenance_url)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1;", db_name)
        if exists:
            return
        logger.info("Database %s não encontrado. Criando automaticamente.", db_name)
        await conn.execute(f"CREATE DATABASE {_quote_ident(db_name)};")
        logger.info("Database %s criado com sucesso.", db_name)
    finally:
        await conn.close()


async def ensure_schema_applied(database_url: str, schema_path: Path, logger: logging.Logger) -> None:
    try:
        import asyncpg  # type: ignore
    except Exception as exc:
        raise RuntimeError("Dependência asyncpg não encontrada. Rode: python -m pip install -r requirements.txt") from exc

    conn = await asyncpg.connect(_normalize_asyncpg_dsn(database_url))
    try:
        usuarios_exists = await conn.fetchval("SELECT to_regclass('public.usuarios') IS NOT NULL;")
        if usuarios_exists:
            return

        logger.info("Schema não encontrado (tabela usuarios ausente). Aplicando %s", schema_path.as_posix())
        sql_script = schema_path.read_text(encoding="utf-8")
        await conn.execute(sql_script)
        logger.info("Schema aplicado com sucesso.")
    finally:
        await conn.close()


def start_uvicorn(config: StartupConfig, logger: logging.Logger) -> None:
    args = [
        sys.executable,
        "-m",
        "uvicorn",
        config.app_import,
        "--host",
        config.host,
        "--port",
        str(config.port),
    ]
    if config.reload:
        args.append("--reload")

    logger.info("Iniciando servidor: %s", " ".join(args))
    subprocess.run(args, check=False)


def run_startup(config: StartupConfig) -> None:
    logger = _configure_logging()
    os.environ["DATABASE_URL"] = config.database_url
    logger.info("DATABASE_URL configurada (mascarada): %s", _mask_database_url(config.database_url))

    ensure_dependencies(config.requirements_path, logger)
    asyncio.run(ensure_database_exists(config.database_url, logger))
    if config.schema_path is not None:
        asyncio.run(ensure_schema_applied(config.database_url, config.schema_path, logger))
    asyncio.run(validate_database_connection(config.database_url, logger))
    start_uvicorn(config, logger)
