from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.auth.dependencies import is_student
from app.auth.course_access import ensure_student_enrolled
from app.helpers.quiz_answer_evaluator import evaluate_quiz_answers
from app.models import Quiz,QuizSubmission,User,QuizQuestion,QuizAnswer
from app.schemas.quiz_submission import (
    QuizSubmitRequest,QuizSubmitResponse,
    QuizSubmissionDetailView,QuizQuestionResult,
    QuizOptionResult
)

router=APIRouter(
    prefix="/student/quiz-submission",
    tags=["Student Quiz Submission Endpoints"]
)

@router.post(
    "/submit-quiz/{quiz_id}",
    response_model=QuizSubmitResponse,
    status_code=201,
)
async def submit_quiz(
    quiz_id: UUID,
    payload: QuizSubmitRequest,
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch quiz with questions
    # --------------------------
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.questions)
            .selectinload(QuizQuestion.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # --------------------------
    # Enrollment check
    # --------------------------
    await ensure_student_enrolled(
        course_id=quiz.course_id,
        student_id=current_user.id,
        db=db,
    )

    # --------------------------
    # Prevent re-submission
    # --------------------------
    result = await db.execute(
        select(QuizSubmission).where(
            QuizSubmission.quiz_id == quiz.id,
            QuizSubmission.student_id == current_user.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "You have already submitted this quiz")

    # --------------------------
    # Create submission
    # --------------------------
    submission = QuizSubmission(
        quiz_id=quiz.id,
        student_id=current_user.id,
    )
    db.add(submission)
    await db.flush()

    # --------------------------
    # Evaluate answers (NEW)
    # --------------------------
    total_score, answer_rows = evaluate_quiz_answers(
        quiz=quiz,
        submission_id=submission.id,
        answers_payload=payload.answers,
    )

    submission.total_score = total_score
    db.add_all(answer_rows)

    # --------------------------
    # Commit
    # --------------------------
    await db.commit()
    await db.refresh(submission)

    return {
        "submission_id": submission.id,
        "quiz_id": quiz.id,
        "total_score": total_score,
    }

@router.get(
    "/my-quiz-result/{quiz_id}",
    response_model=QuizSubmissionDetailView,
)
async def get_my_quiz_result(
    quiz_id: UUID,
    current_user: User = Depends(is_student),
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
    # Enrollment check
    # --------------------------
    await ensure_student_enrolled(
        course_id=quiz.course_id,
        student_id=current_user.id,
        db=db,
    )

    # --------------------------
    # Fetch student's submission
    # --------------------------
    result = await db.execute(
        select(QuizSubmission)
        .options(
            selectinload(QuizSubmission.answers)
            .selectinload(QuizAnswer.selected_option),
            selectinload(QuizSubmission.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.options),
            selectinload(QuizSubmission.student),
        )
        .where(
            QuizSubmission.quiz_id == quiz_id,
            QuizSubmission.student_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=403,
            detail="You have not submitted this quiz",
        )

    # --------------------------
    # Build question results
    # --------------------------
    question_map = {q.id: q for q in submission.quiz.questions}
    answers_map = {a.question_id: a for a in submission.answers}

    question_results = []

    for q in submission.quiz.questions:
        correct_option = next(
            opt for opt in q.options if opt.is_correct
        )

        student_answer = answers_map.get(q.id)
        selected_option = student_answer.selected_option if student_answer else None

        is_correct = (
            selected_option.id == correct_option.id
            if selected_option
            else False
        )

        question_results.append(
            QuizQuestionResult(
                id=q.id,
                question_text=q.question_text,
                marks=q.marks,
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
        quiz_id=submission.quiz_id,
        quiz_title=submission.quiz.title,
        student_id=current_user.id,
        student_roll_number=current_user.roll_number,
        submitted_at=submission.submitted_at,
        total_score=submission.total_score,
        questions=question_results,
    )
