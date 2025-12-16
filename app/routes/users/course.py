from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import UUID

from app.schemas.course import (
    StudentCoursesCursorResponse,CourseBasicItem,CourseDetailResponse
    )
from app.schemas.category import CategoryItem
from app.schemas.week import WeekLite
from app.schemas.media import MediaLite
from app.schemas.quiz import QuizLite
from app.schemas.assignment import AssignmentLite
from app.models import Course,User,CourseWeek,course_students,Quiz,Media,Assignment
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.course_access import check_course_access

router = APIRouter(
    prefix="/course",
    tags=["User Course Endpoints"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/list-courses", response_model=StudentCoursesCursorResponse)
async def list_courses_cursor(
    cursor: str | None = Query(None, description="Cursor timestamp for pagination"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    cursor_time = datetime.fromisoformat(cursor) if cursor else None
    
    query = (
        select(Course)
        .options(
            selectinload(Course.categories)
            )
        )
    
    if cursor_time:
        query = query.where(Course.created_at < cursor_time)

    query = query.order_by(Course.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    courses = result.scalars().all()

    # Cursor logic
    if len(courses) > limit:
        next_cursor = courses[limit-1].created_at.isoformat()
        courses = courses[:limit]
    else:
        next_cursor = None

    # Fetch week counts
    course_ids = [c.id for c in courses]

    week_count_map = {}

    if course_ids:
        week_rows = await db.execute(
            select(CourseWeek.course_id, func.count(CourseWeek.id))
            .where(CourseWeek.course_id.in_(course_ids))
            .group_by(CourseWeek.course_id)
        )
        week_count_map = {str(r[0]): r[1] for r in week_rows.all()}

    return StudentCoursesCursorResponse(
        limit=limit,
        next_cursor=next_cursor,
        data=[
            CourseBasicItem(
                id=str(c.id),
                code=c.code,
                name=c.name,
                description=c.description,
                credits=c.credits,
                thumbnail=c.thumbnail,
                number_of_weeks=week_count_map.get(str(c.id), 0) , # ⬅️ ADDED
                categories=[
                    CategoryItem(
                        id=str(cat.id),
                        name=cat.name
                    )
                    for cat in c.categories
                ]
                
            )
            for c in courses
        ]
    )

@router.get("/course-detail/{course_id}", response_model=CourseDetailResponse)
async def get_course_detail(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Validate UUID
    # --------------------------
    try:
        course_uuid = UUID(course_id)
    except ValueError:
        raise HTTPException(400, "Invalid course ID")

    # --------------------------
    # Fetch course + instructor + weeks
    # --------------------------
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.instructor),
            selectinload(Course.weeks),
            selectinload(Course.categories)
        )
        .where(Course.id == course_uuid)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(404, "Course not found")

    # --------------------------
    # Count enrolled students
    # --------------------------
    enrolled_count = await db.scalar(
        select(func.count(course_students.c.student_id))
        .where(course_students.c.course_id == course_uuid)
    ) or 0

    # --------------------------
    # Permission check
    # --------------------------
    try:
        await check_course_access(course_id, current_user, db)
        has_full_access = True
    except HTTPException:
        has_full_access = False

    # --------------------------
    # BASIC VIEW (no access)
    # --------------------------
    if not has_full_access:
        return CourseDetailResponse(
            id=str(course.id),
            code=course.code,
            name=course.name,
            description=course.description,
            credits=course.credits,
            thumbnail=course.thumbnail,
            categories=[
                CategoryItem(
                    id=str(cat.id),
                    name=cat.name
                )
                for cat in course.categories
            ],
            instructor_name=course.instructor.name if course.instructor else None,
            instructor_id=str(course.instructor_id),
            enrolled_count=enrolled_count,
            media_items=[],
            assignments=[],
            quizzes=[],
            weeks=[WeekLite(id=str(w.id)) for w in course.weeks],
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    # --------------------------
    # FULL VIEW (global items only)
    # --------------------------

    # Media (week_id IS NULL)
    media_result = await db.execute(
        select(Media).where(
            Media.course_id == course_uuid,
            Media.week_id.is_(None)
        )
    )
    media_db = media_result.scalars().all()

    # Assignments (week_id IS NULL)
    assignment_result = await db.execute(
        select(Assignment).where(
            Assignment.course_id == course_uuid,
            Assignment.week_id.is_(None)
        )
    )
    assignments_db = assignment_result.scalars().all()

    # Quizzes (week_id IS NULL) + questions
    quiz_result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(
            Quiz.course_id == course_uuid,
            Quiz.week_id.is_(None)
        )
    )
    quizzes_db = quiz_result.scalars().all()

    # --------------------------
    # Convert to response objects
    # --------------------------
    media_items = [
        MediaLite(
            id=str(m.id),
            title=m.title,
            file_url=m.file_url,
            media_type=m.media_type,
            duration_seconds=m.duration_seconds
        )
        for m in media_db
    ]

    assignments = [
        AssignmentLite(
            id=str(a.id),
            title=a.title,
            deadline=a.deadline,
            total_marks=a.total_marks,
            description=a.description
        )
        for a in assignments_db
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
        for q in quizzes_db
    ]

    weeks = [WeekLite(id=str(w.id)) for w in course.weeks]

    # --------------------------
    # Final response
    # --------------------------
    return CourseDetailResponse(
        id=str(course.id),
        code=course.code,
        name=course.name,
        description=course.description,
        credits=course.credits,
        thumbnail=course.thumbnail,
        categories=[
                CategoryItem(
                    id=str(cat.id),
                    name=cat.name
                )
                for cat in course.categories
            ],
        instructor_name=course.instructor.name if course.instructor else None,
        instructor_id=str(course.instructor_id),
        enrolled_count=enrolled_count,
        media_items=media_items,
        assignments=assignments,
        quizzes=quizzes,
        weeks=weeks,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )
