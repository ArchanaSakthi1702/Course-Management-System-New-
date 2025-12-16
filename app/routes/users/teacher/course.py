from fastapi import APIRouter, Depends, HTTPException,Query,Form,UploadFile,File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime
import os
from uuid import uuid4,UUID
import aiofiles
from typing import Optional,List

from app.database import get_db
from app.models import Course, User,Media,Assignment,course_students,CourseCategory
from app.helpers.file_paths import get_thumbnail_fs_path,get_media_fs_path,THUMBNAIL_UPLOAD_DIR,delete_assignment_file_safely
from app.helpers.progress_calculator import get_assignment_performance,get_quiz_performance
from app.schemas.course import CourseBulkDelete,MyCoursesCursorResponse,CourseItem
from app.schemas.category import CategoryItem
from app.auth.dependencies import is_teacher


router = APIRouter(
    prefix="/teacher/course",
    tags=["Teacher Course Endpoints"]
    )

@router.post("/create-course", status_code=201)
async def create_course(
    code:str=Form(...),
    name:str=Form(...),
    description:Optional[str]=Form(None),
    credits:Optional[int]=Form(None),
    category_ids: Optional[List[UUID]] = Form(None),
    thumbnail: UploadFile = File(None),
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):

    existing = await db.execute(
        select(Course).where(Course.code ==code)
    )
    if existing.scalars().first():
        raise HTTPException(400, "Course code already exists")

    # --------------------------
    # Handle thumbnail upload
    # --------------------------
    thumbnail_url = None

    if thumbnail:
        os.makedirs(THUMBNAIL_UPLOAD_DIR, exist_ok=True)

        ext = os.path.splitext(thumbnail.filename)[1]
        if not ext:
            raise HTTPException(400, "Invalid thumbnail file")

        filename = f"{uuid4()}{ext}"
        fs_path = os.path.join(THUMBNAIL_UPLOAD_DIR, filename)

        async with aiofiles.open(fs_path, "wb") as f:
            await f.write(await thumbnail.read())

        thumbnail_url = f"/uploads/thumbnails/{filename}"


    # --------------------------
    # Create course
    # --------------------------
    new_course = Course(
        code=code,
        name=name,
        description=description,
        credits=credits,
        instructor_id=current_user.id,
        thumbnail=thumbnail_url
    )

    if category_ids:
        result = await db.execute(
            select(CourseCategory).where(CourseCategory.id.in_(category_ids))
        )
        categories = result.scalars().all()
        new_course.categories = categories

    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)

    return {
        "message": "Course created successfully",
        "course_id": str(new_course.id)
    }


@router.patch("/update-course/{course_id}")
async def update_course(
    course_id: UUID,
    code: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_ids: Optional[List[UUID]] = Form(None),
    credits: Optional[int] = Form(None),
    thumbnail: UploadFile = File(None),
    is_course_ended: Optional[bool] = Form(None),
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalars().first()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Not allowed to update this course")

    # Uniqueness check (only if code changes)
    if code and code != course.code:
        existing = await db.execute(
            select(Course).where(Course.code == code)
        )
        if existing.scalars().first():
            raise HTTPException(400, "Course code already exists")

    # Update fields
    if code is not None:
        course.code = code
    if name is not None:
        course.name = name
    if description is not None:
        course.description = description
    if credits is not None:
        course.credits = credits
    if category_ids is not None:
        if len(category_ids) == 0:
            # 🔥 Clear all categories
            course.categories = []
        else:
            result = await db.execute(
                select(CourseCategory).where(CourseCategory.id.in_(category_ids))
            )
            categories = result.scalars().all()
            course.categories = categories
    if is_course_ended is not None:
        course.is_course_ended = is_course_ended

    # Thumbnail update
    if thumbnail:
        os.makedirs(THUMBNAIL_UPLOAD_DIR, exist_ok=True)

    # delete old thumbnail
        if course.thumbnail:
            old_fs_path = get_thumbnail_fs_path(course.thumbnail)
            if os.path.exists(old_fs_path):
                os.remove(old_fs_path)

        ext = os.path.splitext(thumbnail.filename)[1]
        if not ext:
            raise HTTPException(400, "Invalid thumbnail file")

        filename = f"{uuid4()}{ext}"
        fs_path = os.path.join(THUMBNAIL_UPLOAD_DIR, filename)

        async with aiofiles.open(fs_path, "wb") as f:
            await f.write(await thumbnail.read())

        course.thumbnail = f"/uploads/thumbnails/{filename}"


    try:
        await db.commit()
        await db.refresh(course)
    except Exception:
        await db.rollback()
        raise

    return {
        "message": "Course updated successfully",
        "course_id": str(course.id)
    }

@router.delete("/delete-course/{course_id}")
async def delete_course(
    course_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.assignments)
            .selectinload(Assignment.submissions)
        )
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "You cannot delete this course")

    # --------------------------
    # Delete assignment submission files
    # --------------------------
    for assignment in course.assignments:
        for submission in assignment.submissions:
            delete_assignment_file_safely(submission.file_url)

    # --------------------------
    # Delete media files
    # --------------------------
    result = await db.execute(select(Media).where(Media.course_id == course.id))
    media_files = result.scalars().all()

    for media in media_files:
        fs_path = get_media_fs_path(media.file_url)
        if os.path.exists(fs_path):
            os.remove(fs_path)

    # --------------------------
    # Delete thumbnail file
    # --------------------------
    if course.thumbnail:
        fs_path = get_thumbnail_fs_path(course.thumbnail)
        if os.path.exists(fs_path):
            os.remove(fs_path)

    await db.delete(course)
    await db.commit()

    return {"message": "Course deleted successfully", "course_id": course_id}



@router.delete("/bulk-delete")
async def bulk_delete_courses(
    data: CourseBulkDelete,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    deleted = []

    result = await db.execute(
        select(Course)
        .where(Course.id.in_(data.course_ids))
        .options(
            selectinload(Course.assignments)
            .selectinload(Assignment.submissions)
        )
    )
    courses = result.scalars().all()

    for course in courses:
        if course.instructor_id != current_user.id:
            continue

        # --------------------------
        # Delete assignment submission files
        # --------------------------
        for assignment in course.assignments:
            for submission in assignment.submissions:
                delete_assignment_file_safely(submission.file_url)

        # --------------------------
        # Delete media files
        # --------------------------
        result = await db.execute(select(Media).where(Media.course_id == course.id))
        media_files = result.scalars().all()

        for media in media_files:
            fs_path = get_media_fs_path(media.file_url)
            if os.path.exists(fs_path):
                os.remove(fs_path)

        # --------------------------
        # Delete thumbnail
        # --------------------------
        if course.thumbnail:
            fs_path = get_thumbnail_fs_path(course.thumbnail)
            if os.path.exists(fs_path):
                os.remove(fs_path)

        await db.delete(course)
        deleted.append(course.id)

    await db.commit()

    return {
        "message": "Bulk delete completed",
        "deleted_courses": deleted,
        "count": len(deleted),
    }



@router.get("/my-courses",response_model=MyCoursesCursorResponse)
async def list_my_courses_cursor(
    cursor: str | None = Query(None, description="Timestamp cursor for pagination"),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Cursor-based pagination for teacher's courses.
    Ultra-fast and efficient (no OFFSET).
    """
    print(f"{cursor} <-This is cursor")
    # Convert cursor string to datetime if provided
    cursor_time = None
    if cursor:
        try:
            cursor_time = datetime.fromisoformat(cursor)
            print("For Real")
        except Exception:
            raise HTTPException(400, "Invalid cursor timestamp")

    # Base query
    query = (
            select(Course)
            .where(Course.instructor_id == current_user.id).
            options(selectinload(Course.categories))
            )

    # Add cursor condition (fetch older items only)
    if cursor_time:
        query = query.where(Course.created_at < cursor_time)

    # Order + limit (fetch 1 extra to detect next cursor)
    query = query.order_by(Course.created_at.desc()).limit(limit+1)

    result = await db.execute(query)
    courses = result.scalars().all()

    # Determine next cursor
    if len(courses) > limit:
        next_cursor = courses[limit-1].created_at.isoformat()
        courses = courses[:limit]
    else:
        next_cursor = None

    return MyCoursesCursorResponse(
        teacher_id=str(current_user.id),
        limit=limit,
        next_cursor=next_cursor,
        data=[
            CourseItem(
                id=str(c.id),
                code=c.code,
                name=c.name,
                description=c.description,
                credits=c.credits,
                categories=[
                CategoryItem(
                    id=str(cat.id),
                    name=cat.name
                )
                for cat in c.categories],
                created_at=c.created_at,
                updated_at=c.updated_at,
                thumbnail=c.thumbnail
            )
            for c in courses
        ]
    )



@router.get("/students-performance/{course_id}")
async def get_course_students_performance(
    course_id: UUID,
    cursor: Optional[str] = Query(None, description="Use to fetch next batch after this created_at ISO timestamp"),
    limit: int = Query(10, description="Number of students to fetch per request"),
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch course
    # --------------------------
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found")
    if course.instructor_id != current_user.id:
        raise HTTPException(403, "You are not the instructor of this course")

    # --------------------------
    # Fetch students with cursor using created_at
    # --------------------------
    query = select(User).join(course_students, course_students.c.student_id == User.id).where(
        course_students.c.course_id == course_id
    )
    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(400, "Invalid cursor format. Use ISO datetime string.")
        query = query.where(User.created_at > cursor_dt)

    query = query.order_by(User.created_at).limit(limit)
    result = await db.execute(query)
    students = result.scalars().all()

    if not students:
        return {"course_id": course.id, "course_name": course.name, "students_performance": [], "next_cursor": None}

    # --------------------------
    # Calculate performance
    # --------------------------
    students_data = []
    for student in students:
        assignment_perf = await get_assignment_performance(course_id, student.id, db)
        quiz_perf = await get_quiz_performance(course_id, student.id, db)
        students_data.append({
            "student_id": student.id,
            "student_name": student.name,
            "student_roll_number": student.roll_number,
            "created_at": student.created_at,
            "assignment_obtained": assignment_perf["obtained"],
            "assignment_total": assignment_perf["total"],
            "assignment_percentage": assignment_perf["percentage"],
            "quiz_obtained": quiz_perf["obtained"],
            "quiz_total": quiz_perf["total"],
            "quiz_percentage": quiz_perf["percentage"],
        })

    # Last student created_at for next cursor
    next_cursor = students_data[-1]["created_at"].isoformat() if students_data else None

    return {
        "course_id": course.id,
        "course_name": course.name,
        "students_performance": students_data,
        "next_cursor": next_cursor
    }