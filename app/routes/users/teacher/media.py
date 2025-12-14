from fastapi import APIRouter,Depends,HTTPException,Form,UploadFile,File
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import os 
from uuid import uuid4,UUID
import aiofiles
from typing import Optional


from app.models import User, Course, CourseWeek, Media
from app.database import get_db
from app.helpers.file_paths import MEDIA_UPLOAD_DIR, get_media_fs_path
from app.auth.dependencies import is_teacher
from app.schemas.media import MediaBulkDelete

router = APIRouter(
    tags=["Teacher Media Endpoints"],
    prefix="/teacher/media"
)

@router.post("/upload-media/{course_id}")
async def upload_media(
    course_id: str,
    week_id: str | None = Form(None),   # optional week
    title: str = Form(...),
    media_type: str = Form(...),
    file: UploadFile = File(...),
    duration_seconds:Optional[int]=Form(None),
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Validate course
    # --------------------------
    try:
        course_uuid = UUID(course_id)
    except ValueError:
        raise HTTPException(400, "Invalid course ID format")

    result = await db.execute(select(Course).where(Course.id == course_uuid))
    course = result.scalars().first()
    if not course:
        raise HTTPException(404, "Course not found")

    # Check ownership
    if course.instructor_id != current_user.id:
        raise HTTPException(403, "You cannot add media to this course")

    # --------------------------
    # Validate week (optional)
    # --------------------------
    week_obj = None
    if week_id:
        try:
            week_uuid = UUID(week_id)
        except ValueError:
            raise HTTPException(400, "Invalid week ID format")

        result = await db.execute(
            select(CourseWeek).where(CourseWeek.id == week_uuid, CourseWeek.course_id == course.id)
        )
        week_obj = result.scalars().first()
        if not week_obj:
            raise HTTPException(404, "Week not found for this course")

    # --------------------------
    # Save file
    # --------------------------
    os.makedirs(MEDIA_UPLOAD_DIR, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"
    fs_path = os.path.join(MEDIA_UPLOAD_DIR, filename)

    async with aiofiles.open(fs_path, "wb") as f:
        await f.write(await file.read())


    if media_type != "video":
        duration_seconds = None
    # --------------------------
    # Create Media record
    # --------------------------
    media = Media(
        course_id=course.id,
        week_id=week_obj.id if week_obj else None,
        uploaded_by=current_user.id,
        title=title,
        file_url=f"/uploads/media/{filename}",
        media_type=media_type,
        duration_seconds=duration_seconds
    )

    db.add(media)
    await db.commit()
    await db.refresh(media)

    return {
        "message": "Media uploaded successfully",
        "media_id": str(media.id),
        "week_id": str(media.week_id) if media.week_id else None
    }



@router.put("/update-media/{media_id}")
async def update_media(
    media_id: str,
    title: str = Form(...),
    media_type: str = Form(...),
    duration_seconds:Optional[int]=Form(None),
    week_id: str | None = Form(None),          # optional: move to another week or set None for global
    file: UploadFile | None = File(None),     # optional: replace file
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Validate media
    # --------------------------
    try:
        media_uuid = UUID(media_id)
    except ValueError:
        raise HTTPException(400, "Invalid media ID format")

    result = await db.execute(
        select(Media)
        .options(selectinload(Media.course))
        .where(Media.id == media_uuid)
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(404, "Media not found")

    # --------------------------
    # Check instructor permission
    # --------------------------
    if media.course.instructor_id != current_user.id:
        raise HTTPException(403, "You cannot edit this media")

    # --------------------------
    # Validate new week (optional)
    # --------------------------
    if week_id:
        try:
            week_uuid = UUID(week_id)
        except ValueError:
            raise HTTPException(400, "Invalid week ID format")

        result = await db.execute(
            select(CourseWeek).where(
                CourseWeek.id == week_uuid,
                CourseWeek.course_id == media.course_id
            )
        )
        week_obj = result.scalar_one_or_none()
        if not week_obj:
            raise HTTPException(404, "Week not found for this course")
        media.week_id = week_obj.id
    else:
        media.week_id = None  # Make it global if week_id not provided

    # --------------------------
    # Update metadata
    # --------------------------
    media.title = title
    media.media_type = media_type
    media.duration_seconds = duration_seconds if media_type == "video" else None

    # --------------------------
    # Replace file if new file uploaded
    # --------------------------
    if file:
        os.makedirs(MEDIA_UPLOAD_DIR, exist_ok=True)

        new_filename = f"{uuid4()}.{file.filename.split('.')[-1]}"
        new_fs_path = os.path.join(MEDIA_UPLOAD_DIR, new_filename)

        async with aiofiles.open(new_fs_path, "wb") as f:
            await f.write(await file.read())

        old_fs_path = get_media_fs_path(media.file_url)
        if os.path.exists(old_fs_path):
            os.remove(old_fs_path)

        media.file_url = f"/uploads/media/{new_filename}"

    db.add(media)
    await db.commit()
    await db.refresh(media)

    return {
        "message": "Media updated successfully",
        "media_id": str(media.id),
        "title": media.title,
        "media_type": media.media_type,
        "file_url": media.file_url,
        "week_id": str(media.week_id) if media.week_id else None
    }


@router.delete("/delete-media/{media_id}")
async def delete_media(
    media_id: str,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # Validate media ID
    try:
        media_uuid = UUID(media_id)
    except ValueError:
        raise HTTPException(400, "Invalid media ID format")

    # Fetch media with course (eager load course for permission check)
    result = await db.execute(
        select(Media)
        .options(selectinload(Media.course))
        .where(Media.id == media_uuid)
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(404, "Media not found")

    # Permission check
    if media.course.instructor_id != current_user.id:
        raise HTTPException(403, "You cannot delete this media")

    # Delete the file from disk
    fs_path = get_media_fs_path(media.file_url)
    if os.path.exists(fs_path):
        os.remove(fs_path)

    # Delete from DB
    await db.delete(media)
    await db.commit()

    return {"message": "Media deleted successfully", "media_id": str(media.id)}




@router.delete("/bulk-delete")
async def bulk_delete_media(
    payload: MediaBulkDelete,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    deleted_ids = []

    for media_id in payload.media_ids:
        try:
            media_uuid = UUID(media_id)
        except ValueError:
            continue  # skip invalid UUIDs

        result = await db.execute(
            select(Media)
            .options(selectinload(Media.course))
            .where(Media.id == media_uuid)
        )
        media = result.scalar_one_or_none()
        if not media or media.course.instructor_id != current_user.id:
            continue  # skip media not found or no permission

        # Delete file
        fs_path = get_media_fs_path(media.file_url)
        if os.path.exists(fs_path):
            os.remove(fs_path)

        # Delete DB record
        await db.delete(media)
        deleted_ids.append(str(media.id))

    await db.commit()

    return {
        "message": "Bulk delete completed",
        "deleted_ids": deleted_ids
    }