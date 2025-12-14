from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models import Course, course_students, User



async def check_course_access(course_id: str, current_user: User, db: AsyncSession):
    """Allows access if the user is either enrolled OR the course instructor."""

    # Check if instructor
    stmt = select(Course).where(
        Course.id == course_id,
        Course.instructor_id == current_user.id
    )
    result = await db.execute(stmt)
    course = result.scalar_one_or_none()

    if course:
        return True  # User is instructor

    # Check if enrolled
    stmt = select(course_students).where(
        course_students.c.course_id == course_id,
        course_students.c.student_id == current_user.id
    )
    result = await db.execute(stmt)
    enrolled = result.first()

    if enrolled:
        return True  # User is enrolled

    # Neither student nor instructor
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have access to this course."
    )


async def ensure_student_enrolled(
    course_id: UUID,
    student_id: UUID,
    db: AsyncSession,
):
    result = await db.execute(
        select(course_students).where(
            course_students.c.course_id == course_id,
            course_students.c.student_id == student_id,
        )
    )
    if not result.first():
        raise HTTPException(403, "You are not enrolled in this course")