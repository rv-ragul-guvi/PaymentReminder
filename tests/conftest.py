import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.course import Course
from app.channels.email import mock_sent_emails

# In-memory database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    """Create fresh in-memory schema for each test session"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed sample course
    async with TestingSessionLocal() as session:
        course = Course(
            id="COURSE-TEST-001",
            title="Full Stack Python Development",
            description="Complete Python bootcamp",
            full_price=40000.0,
            down_payment_amount=5000.0,
            currency="INR",
        )
        session.add(course)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def clear_mock_emails():
    """Clear captured emails between tests and enforce MOCK mode during test runs"""
    original_mode = settings.EMAIL_MODE
    settings.EMAIL_MODE = "MOCK"
    mock_sent_emails.clear()
    yield
    mock_sent_emails.clear()
    settings.EMAIL_MODE = original_mode


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session
