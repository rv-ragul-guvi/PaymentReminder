from fastapi import APIRouter
from app.api.v1.courses import router as courses_router
from app.api.v1.payment_links import router as payment_links_router
from app.api.v1.payments import router as payments_router
from app.api.v1.reminders import router as reminders_router

api_router = APIRouter()
api_router.include_router(courses_router)
api_router.include_router(payment_links_router)
api_router.include_router(payments_router)
api_router.include_router(reminders_router)
