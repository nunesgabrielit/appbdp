from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.startup import StartupConfig, run_startup


def main() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL não está configurada. Crie um arquivo .env na raiz do projeto "
            "com uma linha como: DATABASE_URL=postgresql+asyncpg://usuario:gabriel15@localhost:5432/bdp_app"
        )

    config = StartupConfig(
        database_url=database_url,
        requirements_path=Path(__file__).resolve().parent / "requirements.txt",
        schema_path=Path(__file__).resolve().parent / "database" / "01_init_schema.sql",
        app_import="app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
    run_startup(config)


if __name__ == "__main__":
    main()
