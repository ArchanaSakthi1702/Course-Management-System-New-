from fastapi import APIRouter, Depends, HTTPException,status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models import CourseWeek, Quiz, User
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.schemas.course import MediaLite, AssignmentLite, QuizLite, WeekLite
from app.auth.course_access import check_course_access

router = APIRouter(
    prefix="/week",
    tags=["User Week Endpoints"]
)

@router.get("/list-weeks-in-course/{course_id}", response_model=list[WeekLite],dependencies=[Depends(get_current_user)])
async def list_course_weeks(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CourseWeek.id).where(CourseWeek.course_id == course_id)
    )
    week_ids = result.scalars().all()

    return [WeekLite(id=str(week_id)) for week_id in week_ids]


@router.get("/week-details/{week_id}", response_model=dict)
async def get_week_detail(
    week_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # --------------------------
    # Fetch week with course
    # --------------------------
    result = await db.execute(
        select(CourseWeek)
        .options(
            selectinload(CourseWeek.media_items),
            selectinload(CourseWeek.assignments),
            selectinload(CourseWeek.quizzes).selectinload(Quiz.questions),
            selectinload(CourseWeek.course)
        )
        .where(CourseWeek.id == week_id)
    )
    week = result.scalar_one_or_none()
    if not week:
        raise HTTPException(404, "Week not found")

    # --------------------------
    # Permission: only instructor or enrolled students
    # --------------------------
    course_id = str(week.course_id)
    try:
        await check_course_access(course_id, current_user, db)
    except HTTPException:
        raise HTTPException(status_code=403, detail="You don't have access to this week.")

    # --------------------------
    # Build response
    # --------------------------
    media_items = [
        MediaLite(
            id=str(m.id),
            title=m.title,
            file_url=m.file_url,
            media_type=m.media_type
        )
        for m in week.media_items
    ]

    assignments = [
        AssignmentLite(
            id=str(a.id),
            title=a.title,
            deadline=a.deadline,
            total_marks=a.total_marks,
            description=a.description
        )
        for a in week.assignments
    ]

    quizzes = [
        QuizLite(
            id=str(q.id),
            title=q.title,
            total_marks=q.total_marks,
            description=q.description,
            time_limit_minutes=q.time_limit_minutes,
            no_of_questions=len(q.questions)
        )
        for q in week.quizzes
    ]

    return {
        "week": WeekLite(id=str(week.id)),
        "week_number": week.week_number,
        "title": week.title,
        "description": week.description,
        "media_items": media_items,
        "assignments": assignments,
        "quizzes": quizzes,
        "course_id": str(week.course_id)
    }
