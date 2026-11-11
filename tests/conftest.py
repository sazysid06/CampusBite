import asyncio
import os
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.engine import URL

# The checked-in .env uses the Docker-only /app/data mount.
TEST_DATABASE_PATH = Path(gettempdir()) / f"campusbite-test-{uuid4().hex}.db"
os.environ["JWT_SECRET_KEY"] = "campusbite-test-only-key"
os.environ["DATABASE_URL"] = URL.create(
    "sqlite+aiosqlite", database=str(TEST_DATABASE_PATH)
).render_as_string(hide_password=False)

from backend.app.main import app
from backend.app.core.database import Base, engine
from backend.scripts.seed import seed_database
import backend.app.models  # Ensures all models are registered in Base.metadata


@pytest_asyncio.fixture(loop_scope="function", autouse=True)
async def setup_test_database():
    """Create all registered database tables before tests run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_database()
    yield


@pytest_asyncio.fixture(loop_scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def pytest_sessionfinish(session, exitstatus):
    asyncio.run(engine.dispose())
    for suffix in ("", "-wal", "-shm"):
        database_file = TEST_DATABASE_PATH.with_name(TEST_DATABASE_PATH.name + suffix)
        database_file.unlink(missing_ok=True)
