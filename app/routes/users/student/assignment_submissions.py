from fastapi import APIRouter, Depends, HTTPException,UploadFile,File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime,timezone
import shutil
import os

from app.models import Assignment, AssignmentSubmission, User,Course
from app.database import get_db
from app.auth.dependencies import is_student
from app.schemas.assignment_submission import  AssignmentSubmissionRead
from app.helpers.file_paths import ASSIGNMENT_SUBMISSION_DIR

router = APIRouter(
    prefix="/student/assignment-submission",
    tags=["Student Assignment Endpoints"]
)

# ---------------------------
# Submit Assignment
# ---------------------------
@router.post("/submit-assignment/{assignment_id}", response_model=AssignmentSubmissionRead)
async def submit_assignment(
    assignment_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ Fetch assignment with course + students eagerly
    result = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.course)
            .selectinload(Course.students))
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    # 2️⃣ Check enrollment
    if current_user.id not in [s.id for s in assignment.course.students]:
        raise HTTPException(403, "You are not enrolled in this course")

    # 3️⃣ Check deadline
    if datetime.now(timezone.utc) > assignment.deadline:
        raise HTTPException(400, "Deadline has passed")

    # 4️⃣ Prevent multiple submissions
    result_sub = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == current_user.id
        )
    )
    existing_submission = result_sub.scalar_one_or_none()
    if existing_submission:
        raise HTTPException(400, "You have already submitted this assignment")

    # 5️⃣ Save uploaded file in assignment_submissions folder
    filename = f"{assignment.id}_{current_user.id}_{file.filename}"
    file_path = os.path.join(ASSIGNMENT_SUBMISSION_DIR, filename)

    os.makedirs(ASSIGNMENT_SUBMISSION_DIR, exist_ok=True)  # ensure folder exists

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_url = f"/uploads/assignment_submissions/{filename}"  # relative URL for DB

    # 6️⃣ Create AssignmentSubmission record
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        student_id=current_user.id,
        file_url=file_url
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return submission

# ---------------------------
# Get All Submissions of Current Student
# ---------------------------
@router.get("/my-assignment-submissions", response_model=list[AssignmentSubmissionRead])
async def get_my_submissions(
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.student_id == current_user.id)
    )
    submissions = result.scalars().all()
    return submissions
