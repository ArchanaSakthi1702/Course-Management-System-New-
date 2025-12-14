from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models import Course,course_students,User
from app.auth.dependencies import is_student
from app.auth.course_access import ensure_student_enrolled
from app.schemas.course import EnrollmentResponse,StudentCourseListResponse
from app.helpers.progress_calculator import get_course_progress,get_quiz_performance,get_assignment_performance

router=APIRouter(
    prefix="/student/course",
    tags=["Student Course Endpoints"]
)



@router.post("/enroll-course/{course_id}", response_model=EnrollmentResponse)
async def enroll_student(
    course_id: str,
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll a student into a course.
    Only STUDENTS can enroll.
    """

    # 1. Check if course exists
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. Check if already enrolled
    exists = await db.execute(
        select(course_students)
        .where(course_students.c.course_id == course_id)
        .where(course_students.c.student_id == current_user.id)
    )

    if exists.first():
        raise HTTPException(400, "Already enrolled in this course")

    # 3. Insert enrollment
    await db.execute(
        course_students.insert().values(
            course_id=course_id,
            student_id=current_user.id
        )
    )

    await db.commit()

    return EnrollmentResponse(
        message="Enrolled successfully",
        course_id=course_id,
        student_id=str(current_user.id)
    )


@router.get(
    "/my-courses",
    response_model=StudentCourseListResponse
)
async def list_student_courses(
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course)
        .join(course_students)
        .options(selectinload(Course.instructor))
        .where(course_students.c.student_id == current_user.id)
        .order_by(Course.created_at.desc())
    )

    courses = result.scalars().all()

    return {
        "courses": [
            {
                "id": course.id,
                "code": course.code,
                "name": course.name,
                "description": course.description,
                "credits": course.credits,
                "thumbnail": course.thumbnail,
                "instructor_name": course.instructor.name if course.instructor else None,
            }
            for course in courses
        ]
    }


@router.get("/course-progress/{course_id}")
async def student_course_progress(
    course_id: UUID,
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db)
):
    # ensure enrollment
    await ensure_student_enrolled(course_id, current_user.id, db)

    progress = await get_course_progress(course_id, current_user.id, db)
    return progress


@router.get("/course-performance/{course_id}")
async def student_course_performance(
    course_id: UUID,
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db)
):
    # Ensure student is enrolled
    await ensure_student_enrolled(course_id, current_user.id, db)

    assignment_perf = await get_assignment_performance(course_id, current_user.id, db)
    quiz_perf = await get_quiz_performance(course_id, current_user.id, db)

    return {
        "assignment": assignment_perf,
        "quiz": quiz_perf
    }


