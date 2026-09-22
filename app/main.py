import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.models.course import Course
from app.api.v1 import api_router
from app.worker import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("guvi.main")


async def init_db_and_seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")

    # Seed initial popular GUVI courses if empty
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(select(Course))
        courses = result.scalars().all()
        if not courses:
            sample_courses = [
                Course(
                    id="FSD-MERN-001",
                    title="Full Stack Development (MERN Specialization)",
                    description="Comprehensive Full Stack Web Development program with 100% placement support.",
                    full_price=55000.0,
                    down_payment_amount=5000.0,
                    currency="INR",
                ),
                Course(
                    id="DATA-AI-002",
                    title="Data Science & Artificial Intelligence with GenAI",
                    description="Master Data Science, Machine Learning, Deep Learning, and LLMs with IIT-M certification.",
                    full_price=65000.0,
                    down_payment_amount=7500.0,
                    currency="INR",
                ),
                Course(
                    id="AUTOMATION-003",
                    title="Automation Testing with Selenium & Python",
                    description="End-to-end SDET and QA Automation Bootcamp.",
                    full_price=35000.0,
                    down_payment_amount=4000.0,
                    currency="INR",
                ),
            ]
            session.add_all(sample_courses)
            await session.commit()
            logger.info(f"Seeded {len(sample_courses)} initial GUVI courses.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up GUVI Payment Reminder Service...")
    await init_db_and_seed()
    start_scheduler()
    yield
    logger.info("Shutting down GUVI Payment Reminder Service...")
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend service to alert on pending and overdue course payments, follow up on shared links, and escalate uncoverted down payments to the GUVI courses team.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "company": settings.COMPANY_NAME,
    }


from pathlib import Path
from fastapi.responses import HTMLResponse

INDEX_HTML_PATH = Path(__file__).parent / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Interactive demo dashboard for GUVI Payment Reminder Service"""
    if INDEX_HTML_PATH.exists():
        return HTMLResponse(content=INDEX_HTML_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>GUVI Payment Reminder Service Dashboard</h1>")

