from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models import Assignment, AssignmentSubmission, User
from app.database import get_db
from app.auth.dependencies import is_teacher
from app.schemas.assignment_submission import AssignmentSubmissionTeacherRead,AssignmentSubmissionGrade,AssignmentSubmissionRead

router = APIRouter(
    prefix="/teacher/assignment-submission",
    tags=["Teacher Assignment Submission Endpoints"]
)

# ------------------------------------
# List all student submissions
# ------------------------------------
@router.get(
    "/list-submissions/{assignment_id}",
    response_model=list[AssignmentSubmissionTeacherRead]
)
async def list_assignment_submissions(
    assignment_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ Fetch assignment
    result = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()

    if not assignment:
        raise HTTPException(404, "Assignment not found")

    # 2️⃣ Ensure teacher owns the assignment
    if assignment.instructor_id != current_user.id:
        raise HTTPException(403, "You are not allowed to view these submissions")

    # 3️⃣ Fetch submissions
    result = await db.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submitted_at.desc())
    )

    submissions = result.scalars().all()
    return submissions



# ---------------------------
# Grade Assignment Submission (Teacher)
# ---------------------------
@router.patch(
    "/update-submission/{submission_id}/",
    response_model=AssignmentSubmissionRead
)
async def grade_submission(
    submission_id: UUID,
    grade_in: AssignmentSubmissionGrade,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # 1️⃣ Fetch submission + assignment
    result = await db.execute(
        select(AssignmentSubmission)
        .join(Assignment)
        .where(AssignmentSubmission.id == submission_id)
        .options(selectinload(AssignmentSubmission.assignment))
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(404, "Submission not found")

    # 2️⃣ Ensure this teacher owns the assignment
    if submission.assignment.instructor_id != current_user.id:
        raise HTTPException(403, "You are not allowed to grade this submission")

    # 3️⃣ Update fields
    if grade_in.marks_obtained is not None:
        submission.marks_obtained = grade_in.marks_obtained

    if grade_in.feedback is not None:
        submission.feedback = grade_in.feedback

    await db.commit()
    await db.refresh(submission)

    return submission
