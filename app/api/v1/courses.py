from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseRead

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course(payload: CourseCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.get(Course, payload.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with ID '{payload.id}' already exists.",
        )
    course = Course(
        id=payload.id,
        title=payload.title,
        description=payload.description,
        full_price=payload.full_price,
        down_payment_amount=payload.down_payment_amount,
        currency=payload.currency,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("", response_model=List[CourseRead])
async def list_courses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Course).order_by(Course.title))
    return list(result.scalars().all())
