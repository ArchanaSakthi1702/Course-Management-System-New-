import uuid
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.helpers.progress_calculator import get_course_progress
from app.models import Certificate


async def issue_certificate_if_completed(
    course_id: UUID,
    student_id: UUID,
    db: AsyncSession
):
    # 1. Get course progress
    progress = await get_course_progress(course_id, student_id, db)

    if progress["overall_progress"] < 90:
        return None  # not eligible yet

    # 2. Check if certificate already exists
    existing = await db.scalar(
        select(Certificate)
        .where(
            Certificate.course_id == course_id,
            Certificate.student_id == student_id
        )
    )

    if existing:
        return existing

    # 3. Create certificate
    cert = Certificate(
        course_id=course_id,
        student_id=student_id,
        certificate_number=f"CERT-{uuid.uuid4().hex[:12].upper()}",
        score=progress["overall_progress"]
    )

    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert
