# app/routes/users/teacher/quizzes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.auth.dependencies import is_teacher
from app.models import Course, Quiz, CourseWeek, User,QuizQuestion,QuizOption
from app.schemas.quiz import QuizCreate, QuizCreateResponse,QuizUpdate,QuizDetailView

router = APIRouter(
    prefix="/teacher/quiz",
    tags=["Teacher Quiz Endpoints"]
)

@router.post(
    "/create-quiz/{course_id}",
    response_model=QuizCreateResponse,
    status_code=201
)
async def create_quiz(
    course_id: UUID,
    quiz_in: QuizCreate,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch course
    # --------------------------
    result = await db.execute(
        select(Course).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(404, "Course not found")

    if course.instructor_id != current_user.id:
        raise HTTPException(403, "Only course instructor can create quizzes")

    # --------------------------
    # Optional week validation
    # --------------------------
    if quiz_in.week_id:
        result = await db.execute(
            select(CourseWeek).where(CourseWeek.id == quiz_in.week_id)
        )
        week = result.scalar_one_or_none()

        if not week:
            raise HTTPException(404, "Week not found")

        if week.course_id != course.id:
            raise HTTPException(400, "Week does not belong to this course")

    # --------------------------
    # Create quiz
    # --------------------------
    quiz = Quiz(
        course_id=course.id,
        instructor_id=current_user.id,
        title=quiz_in.title,
        description=quiz_in.description,
        total_marks=quiz_in.total_marks,
        time_limit_minutes=quiz_in.time_limit_minutes,
        week_id=quiz_in.week_id,
    )

    db.add(quiz)
    await db.flush()  # ⬅ get quiz.id without commit

    # --------------------------
    # Create questions & options
    # --------------------------
    for q in quiz_in.questions:
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q.question_text,
            marks=q.marks,
        )
        db.add(question)
        await db.flush()

        # Validation: at least one correct option
        if not any(opt.is_correct for opt in q.options):
            raise HTTPException(
                400,
                f"Question '{q.question_text}' must have at least one correct option"
            )

        for opt in q.options:
            option = QuizOption(
                question_id=question.id,
                option_text=opt.option_text,
                is_correct=opt.is_correct,
            )
            db.add(option)

    # --------------------------
    # Commit transaction
    # --------------------------
    await db.commit()
    await db.refresh(quiz)

    return {
        "id": quiz.id,
        "title": quiz.title,
        "total_marks": quiz.total_marks,
        "question_count": len(quiz_in.questions),
    }

@router.put(
    "/update-quiz/{quiz_id}",
    response_model=QuizCreateResponse,
)
async def update_quiz(
    quiz_id: UUID,
    quiz_in: QuizUpdate,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch quiz
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
    # Instructor ownership check
    # --------------------------
    if quiz.instructor_id != current_user.id:
        raise HTTPException(403, "Only quiz instructor can update")

    # --------------------------
    # Optional week validation
    # --------------------------
    if quiz_in.week_id:
        result = await db.execute(
            select(CourseWeek).where(CourseWeek.id == quiz_in.week_id)
        )
        week = result.scalar_one_or_none()

        if not week:
            raise HTTPException(404, "Week not found")

        if week.course_id != quiz.course_id:
            raise HTTPException(400, "Week does not belong to this course")

    # --------------------------
    # Update quiz fields
    # --------------------------
    quiz.title = quiz_in.title
    quiz.description = quiz_in.description
    quiz.total_marks = quiz_in.total_marks
    quiz.time_limit_minutes = quiz_in.time_limit_minutes
    quiz.week_id = quiz_in.week_id

    # --------------------------
    # Delete old questions (cascade deletes options)
    # --------------------------
    for question in quiz.questions:
        await db.delete(question)

    await db.flush()

    # --------------------------
    # Recreate questions & options
    # --------------------------
    for q in quiz_in.questions:
        # Validation
        if not any(opt.is_correct for opt in q.options):
            raise HTTPException(
                400,
                f"Question '{q.question_text}' must have at least one correct option"
            )

        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q.question_text,
            marks=q.marks,
        )
        db.add(question)
        await db.flush()

        for opt in q.options:
            db.add(
                QuizOption(
                    question_id=question.id,
                    option_text=opt.option_text,
                    is_correct=opt.is_correct,
                )
            )

    # --------------------------
    # Commit
    # --------------------------
    await db.commit()
    await db.refresh(quiz)

    return {
        "id": quiz.id,
        "title": quiz.title,
        "total_marks": quiz.total_marks,
        "question_count": len(quiz_in.questions),
    }

@router.delete(
    "/delete-quiz/{quiz_id}",
    status_code=204
)
async def delete_quiz(
    quiz_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch quiz
    # --------------------------
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.submissions))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(404, "Quiz not found")

    # --------------------------
    # Ownership check
    # --------------------------
    if quiz.instructor_id != current_user.id:
        raise HTTPException(403, "Only quiz instructor can delete")

    # --------------------------
    # Block deletion if submitted
    # --------------------------
    if quiz.submissions:
        raise HTTPException(
            400,
            "Cannot delete quiz after students have submitted"
        )

    # --------------------------
    # Delete quiz (cascade)
    # --------------------------
    await db.delete(quiz)
    await db.commit()

    return None


@router.get(
    "/quiz-details/{quiz_id}/",
    response_model=QuizDetailView,
)
async def get_quiz_details_teacher(
    quiz_id: UUID,
    current_user: User = Depends(is_teacher),
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
            .selectinload(QuizQuestion.options)
        )
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # --------------------------
    # Instructor ownership check
    # --------------------------
    if quiz.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the instructor of this quiz")

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
                        "is_correct": opt.is_correct,  # original answer included
                    }
                    for opt in q.options
                ],
            }
            for q in quiz.questions
        ],
    )
