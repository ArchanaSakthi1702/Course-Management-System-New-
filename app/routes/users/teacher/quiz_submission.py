from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models import Quiz, QuizSubmission, User,QuizAnswer,QuizQuestion
from app.auth.dependencies import is_teacher
from app.schemas.quiz_submission import QuizSubmissionListItem,QuizOptionResult,QuizQuestionResult,QuizSubmissionDetailView

router = APIRouter(
    prefix="/teacher/quiz-submission",
    tags=["Teacher Quiz Submission Endpoints"]
)

@router.get(
    "/list-quiz-submissions"
    "/{quiz_id}",
    response_model=list[QuizSubmissionListItem],
)
async def list_quiz_submissions_for_teacher(
    quiz_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch quiz
    # --------------------------
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # --------------------------
    # Instructor ownership check
    # --------------------------
    if quiz.instructor_id != current_user.id:
        raise HTTPException(403, "You are not the instructor of this quiz")

    # --------------------------
    # Fetch submissions (ordered)
    # --------------------------
    result = await db.execute(
        select(QuizSubmission)
        .options(selectinload(QuizSubmission.student))
        .where(QuizSubmission.quiz_id == quiz.id)
        .order_by(QuizSubmission.submitted_at.desc())
    )

    submissions = result.scalars().all()

    # --------------------------
    # Response mapping
    # --------------------------
    return [
        QuizSubmissionListItem(
            submission_id=sub.id,
            quiz_id=sub.quiz_id,
            student_id=sub.student_id,
            student_roll_number=sub.student.roll_number,
            total_score=sub.total_score,
            submitted_at=sub.submitted_at,
        )
        for sub in submissions
    ]


@router.get(
    "/quiz-submission-detail/{submission_id}",
    response_model=QuizSubmissionDetailView,
)
async def get_quiz_submission_details_for_teacher(
    submission_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch submission + relations
    # --------------------------
    result = await db.execute(
        select(QuizSubmission)
        .options(
            selectinload(QuizSubmission.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.options),
            selectinload(QuizSubmission.answers)
            .selectinload(QuizAnswer.selected_option),
            selectinload(QuizSubmission.student),
        )
        .where(QuizSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(404, "Submission not found")

    quiz = submission.quiz

    # --------------------------
    # Instructor ownership check
    # --------------------------
    if quiz.instructor_id != current_user.id:
        raise HTTPException(403, "You are not allowed to view this submission")

    # --------------------------
    # Build answer lookup
    # --------------------------
    answer_map = {
        ans.question_id: ans
        for ans in submission.answers
    }

    questions_response = []

    for question in quiz.questions:
        # Correct option
        correct_option = next(
            opt for opt in question.options if opt.is_correct
        )

        answer = answer_map.get(question.id)

        selected_option = answer.selected_option if answer else None

        is_correct = (
            selected_option.id == correct_option.id
            if selected_option
            else False
        )

        questions_response.append(
            QuizQuestionResult(
                id=question.id,
                question_text=question.question_text,
                marks=question.marks,
                selected_option=(
                    QuizOptionResult(
                        id=selected_option.id,
                        option_text=selected_option.option_text,
                        is_correct=selected_option.is_correct,
                    )
                    if selected_option
                    else None
                ),
                correct_option=QuizOptionResult(
                    id=correct_option.id,
                    option_text=correct_option.option_text,
                    is_correct=True,
                ),
                is_correct=is_correct,
            )
        )

    # --------------------------
    # Response
    # --------------------------
    return QuizSubmissionDetailView(
        submission_id=submission.id,
        quiz_id=quiz.id,
        quiz_title=quiz.title,
        student_id=submission.student_id,
        student_roll_number=submission.student.roll_number,
        submitted_at=submission.submitted_at,
        total_score=submission.total_score,
        questions=questions_response,
    )
