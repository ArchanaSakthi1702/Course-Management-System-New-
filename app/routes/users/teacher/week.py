from fastapi import Depends,APIRouter,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import os
from sqlalchemy.orm import selectinload


from app.models import Course,CourseWeek,User,Assignment
from app.database import get_db
from app.auth.dependencies import is_teacher
from app.helpers.file_paths import get_media_fs_path,delete_assignment_file_safely
from app.schemas.week import CreateWeeksRequest,UpdateWeeksRequest,WeekBulkDeleteRequest


router=APIRouter(
    prefix="/teacher/week",
    tags=["Teacher Course Week Endpoints"]

)

@router.post("/create-weeks/{course_id}", status_code=201)
async def create_weeks(
    course_id: str,
    body: CreateWeeksRequest,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch Course
    # --------------------------
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalars().first()

    if not course:
        raise HTTPException(404, "Course not found")

    # Permission check
    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not allowed to add weeks to this course")

    # --------------------------
    # Create Weeks
    # --------------------------
    new_weeks = []

    for w in body.weeks:
        week = CourseWeek(
            course_id=course.id,
            week_number=w.week_number,
            title=w.title,
            description=w.description
        )
        db.add(week)
        new_weeks.append(week)

    await db.commit()

    return {
        "message": "Weeks created successfully",
        "course_id": course_id,
        "created_weeks": [
            {
                "week_number": w.week_number,
                "title": w.title
            }
            for w in new_weeks
        ],
    }


@router.patch("/update-weeks/{course_id}")
async def update_weeks(
    course_id: UUID,
    body: UpdateWeeksRequest,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch Course
    # --------------------------
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalars().first()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not allowed to update weeks")

    updated = []
    created = []

    # --------------------------
    # Process Weeks
    # --------------------------
    for w in body.weeks:
        # --------------------------
        # UPDATE existing week
        # --------------------------
        if w.id:
            result = await db.execute(
                select(CourseWeek).where(
                    CourseWeek.id == UUID(w.id),
                    CourseWeek.course_id == course.id
                )
            )
            week = result.scalars().first()

            if not week:
                raise HTTPException(404, f"Week not found: {w.id}")

            if w.week_number is not None:
                week.week_number = w.week_number
            if w.title is not None:
                week.title = w.title
            if w.description is not None:
                week.description = w.description

            updated.append(week.id)

        # --------------------------
        # CREATE new week
        # --------------------------
        else:
            if w.week_number is None or w.title is None:
                raise HTTPException(
                    400,
                    "week_number and title are required for new weeks"
                )

            week = CourseWeek(
                course_id=course.id,
                week_number=w.week_number,
                title=w.title,
                description=w.description
            )
            db.add(week)
            created.append(w.week_number)

    await db.commit()

    return {
        "message": "Weeks updated successfully",
        "course_id": str(course.id),
        "updated_weeks": updated,
        "created_weeks": created
    }


@router.delete("/delete-week/{course_id}/{week_id}")
async def delete_single_week(
    course_id: UUID,
    week_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch course
    # --------------------------
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalars().first()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not allowed")

    # --------------------------
    # Fetch week with media + assignments + submissions
    # --------------------------
    result = await db.execute(
        select(CourseWeek)
        .options(
            selectinload(CourseWeek.media_items),
            selectinload(CourseWeek.assignments)
            .selectinload(Assignment.submissions)
        )
        .where(
            CourseWeek.id == week_id,
            CourseWeek.course_id == course.id
        )
    )
    week = result.scalars().first()

    if not week:
        raise HTTPException(404, "Week not found")

    # --------------------------
    # Delete media files
    # --------------------------
    for media in week.media_items:
        fs_path = get_media_fs_path(media.file_url)
        if os.path.exists(fs_path):
            os.remove(fs_path)

    # --------------------------
    # Delete assignment submission files
    # --------------------------
    for assignment in week.assignments:
        for submission in assignment.submissions:
            delete_assignment_file_safely(submission.file_url)

    # --------------------------
    # Delete week (DB cascade)
    # --------------------------
    await db.delete(week)
    await db.commit()

    return {
        "message": "Week, media, and assignment submissions deleted successfully",
        "week_id": str(week_id),
    }



@router.delete("/bulk-delete/{course_id}")
async def bulk_delete_weeks(
    course_id: UUID,
    body: WeekBulkDeleteRequest,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch course
    # --------------------------
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalars().first()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not allowed")

    deleted_weeks = []

    # --------------------------
    # Fetch weeks with media + assignments + submissions
    # --------------------------
    result = await db.execute(
        select(CourseWeek)
        .options(
            selectinload(CourseWeek.media_items),
            selectinload(CourseWeek.assignments)
            .selectinload(Assignment.submissions)
        )
        .where(
            CourseWeek.course_id == course.id,
            CourseWeek.id.in_(body.week_ids)
        )
    )
    weeks = result.scalars().all()

    for week in weeks:
        # Delete media files
        for media in week.media_items:
            fs_path = get_media_fs_path(media.file_url)
            if os.path.exists(fs_path):
                os.remove(fs_path)

        # Delete assignment submission files
        for assignment in week.assignments:
            for submission in assignment.submissions:
                delete_assignment_file_safely(submission.file_url)

        await db.delete(week)
        deleted_weeks.append(str(week.id))

    await db.commit()

    return {
        "message": "Weeks, media, and assignment submissions deleted successfully",
        "deleted_weeks": deleted_weeks,
        "count": len(deleted_weeks),
    }
