import os
from collections.abc import AsyncGenerator

import asyncpg
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _normalize_asyncpg_dsn(sqlalchemy_url: str) -> str:
    if sqlalchemy_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + sqlalchemy_url.removeprefix("postgresql+asyncpg://")
    return sqlalchemy_url


@pytest.fixture(scope="session")
def database_url_test() -> str:
    url = os.getenv("DATABASE_URL_TEST")
    if not url:
        pytest.skip("Defina DATABASE_URL_TEST para executar testes de integração com PostgreSQL.")
    return url


@pytest.fixture(scope="session")
async def init_db(database_url_test: str) -> AsyncGenerator[None, None]:
    dsn = _normalize_asyncpg_dsn(database_url_test)
    conn = await asyncpg.connect(dsn)
    try:
        with open(os.path.join("database", "01_init_schema.sql"), encoding="utf-8") as f:
            sql_script = f.read()
        await conn.execute(sql_script)
        yield
    finally:
        await conn.close()


@pytest.fixture
async def test_engine(database_url_test: str, init_db) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(database_url_test, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
async def session(session_maker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        yield session


@pytest.fixture
async def client(session_maker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncClient, None]:
    from app.database import get_session
    from app.main import app

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
