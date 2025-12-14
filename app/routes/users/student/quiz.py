from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Quiz,QuizQuestion,User
from app.auth.dependencies import is_student
from app.schemas.quiz import QuizDetailView
from app.auth.course_access import ensure_student_enrolled


router=APIRouter(
    prefix="/student/quiz",
    tags=["Student Quiz Endpoints"]
)

@router.get(
    "/attend-quiz/{quiz_id}",
    response_model=QuizDetailView,
    response_model_exclude_none=True
)
async def get_quiz_details(
    quiz_id: UUID,
    current_user: User = Depends(is_student),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch quiz + questions + options + week
    # --------------------------
    result = await db.execute(
        select(Quiz)
        .options(
            selectinload(Quiz.week),
            selectinload(Quiz.questions)
            .selectinload(QuizQuestion.options),
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # --------------------------
    # Access control
    # --------------------------
    await ensure_student_enrolled(
            course_id=quiz.course_id,
            student_id=current_user.id,
            db=db,
        )
    
            

    # --------------------------
    # Week mapping
    # --------------------------
    week_data = None
    if quiz.week:
        week_data = {
            "week_number": quiz.week.week_number,
            "title": quiz.week.title,
        }

    # --------------------------
    # Response
    # --------------------------
    return QuizDetailView(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        total_marks=quiz.total_marks,
        time_limit_minutes=quiz.time_limit_minutes,
        week=week_data,
        questions=[
            {
                "id": q.id,
                "question_text": q.question_text,
                "marks": q.marks,
                "options": [
                    {
                        "id": opt.id,
                        "option_text": opt.option_text,
                    }
                    for opt in q.options
                ],
            }
            for q in quiz.questions
        ],
    )
