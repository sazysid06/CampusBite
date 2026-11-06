import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import Base, engine
import backend.app.models  # Ensures all models are registered in Base.metadata


@pytest_asyncio.fixture(loop_scope="function", autouse=True)
async def setup_test_database():
    """Create all registered database tables before tests run."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture(loop_scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac