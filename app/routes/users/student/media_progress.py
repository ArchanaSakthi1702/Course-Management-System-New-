from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Media, MediaProgress
from app.auth.dependencies import is_student
from app.auth.course_access import ensure_student_enrolled
from app.schemas.media_progress import (
    MediaProgressUpdate,
    MediaProgressResponse,
)

router = APIRouter(
    prefix="/student/media-progress", 
    tags=["Student Media Progress Endpoints"])


@router.post(
    "/update-progress",
    response_model=MediaProgressResponse,
    status_code=status.HTTP_200_OK,
)
async def update_media_progress(
    payload: MediaProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(is_student),
):
    # 1️⃣ Fetch media
    media = await db.scalar(
        select(Media).where(Media.id == payload.media_id)
    )

    if not media:
        raise HTTPException(404, "Media not found")

    # 2️⃣ Allow only video tracking
    if media.media_type.lower() != "video":
        raise HTTPException(
            400,
            "Progress tracking allowed only for video media",
        )

    # 3️⃣ Enrollment check (REUSED)
    await ensure_student_enrolled(
        course_id=media.course_id,
        student_id=current_user.id,
        db=db,
    )

    # 4️⃣ Fetch existing progress
    progress = await db.scalar(
        select(MediaProgress).where(
            MediaProgress.media_id == media.id,
            MediaProgress.student_id == current_user.id,
        )
    )

    # 5️⃣ Normalize seconds
    watched_seconds = payload.watched_seconds
    if media.duration_seconds:
        watched_seconds = min(watched_seconds, media.duration_seconds)

    # 6️⃣ Completion rule (90%)
    is_completed = False
    if media.duration_seconds:
        is_completed = watched_seconds >= int(media.duration_seconds * 0.9)

    # 7️⃣ Upsert logic
    if progress:
        progress.watched_seconds = max(
            progress.watched_seconds,
            watched_seconds
        )
        progress.is_completed = progress.is_completed or is_completed
    else:
        progress = MediaProgress(
            media_id=media.id,
            student_id=current_user.id,
            watched_seconds=watched_seconds,
            is_completed=is_completed,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    return MediaProgressResponse(
        media_id=media.id,
        watched_seconds=progress.watched_seconds,
        is_completed=progress.is_completed,
    )
