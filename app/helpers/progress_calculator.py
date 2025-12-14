from sqlalchemy import select, func
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Media,MediaProgress,Assignment,AssignmentSubmission,Quiz,QuizSubmission

async def get_media_progress(course_id: UUID, student_id: UUID, db: AsyncSession):
    # 1. Total duration of all videos in course
    result = await db.execute(
        select(func.sum(Media.duration_seconds))
        .where(Media.course_id == course_id, Media.media_type == "video")
    )
    total_duration = result.scalar()

    if not total_duration:
        return None  # no videos, progress is 0

    # 2. Total seconds watched by student
    result = await db.execute(
        select(func.sum(MediaProgress.watched_seconds))
        .join(Media)
        .where(Media.course_id == course_id, MediaProgress.student_id == student_id)
    )
    watched_seconds = result.scalar() or 0

    # 3. Calculate percentage
    return round((watched_seconds / total_duration) * 100, 2)


async def get_assignment_progress(course_id: UUID, student_id: UUID, db: AsyncSession):
    # Total assignments
    result = await db.execute(
        select(func.count(Assignment.id))
        .where(Assignment.course_id == course_id)
    )
    total_assignments = result.scalar()

    if not total_assignments:
        return None

    # Submitted assignments
    result = await db.execute(
        select(func.count(AssignmentSubmission.id))
        .join(Assignment)
        .where(
            Assignment.course_id == course_id,
            AssignmentSubmission.student_id == student_id
        )
    )
    submitted_assignments = result.scalar() or 0

    return round((submitted_assignments / total_assignments) * 100, 2)

async def get_quiz_progress(course_id: UUID, student_id: UUID, db: AsyncSession):
    # Total quizzes
    result = await db.execute(
        select(func.count(Quiz.id))
        .where(Quiz.course_id == course_id)
    )
    total_quizzes = result.scalar()

    if not total_quizzes:
        return None

    # Completed quizzes (submitted)
    result = await db.execute(
        select(func.count(QuizSubmission.id))
        .join(Quiz)
        .where(
            Quiz.course_id == course_id,
            QuizSubmission.student_id == student_id
        )
    )
    completed_quizzes = result.scalar() or 0

    return round((completed_quizzes / total_quizzes) * 100, 2)


async def get_course_progress(course_id: UUID, student_id: UUID, db: AsyncSession):
    progress_values = []

    video_progress = await get_media_progress(course_id, student_id, db)
    if video_progress is not None:
        progress_values.append(video_progress)

    assignment_progress = await get_assignment_progress(course_id, student_id, db)
    if assignment_progress is not None:
        progress_values.append(assignment_progress)

    quiz_progress = await get_quiz_progress(course_id, student_id, db)
    if quiz_progress is not None:
        progress_values.append(quiz_progress)

    overall = round(sum(progress_values) / len(progress_values), 2) if progress_values else 0

    return {
        "video_progress": video_progress,
        "assignment_progress": assignment_progress,
        "quiz_progress": quiz_progress,
        "overall_progress": overall
    }




async def get_assignment_performance(course_id: UUID, student_id: UUID, db: AsyncSession):
    # 1. Get all assignments in the course
    result = await db.execute(
        select(Assignment.id, Assignment.total_marks)
        .where(Assignment.course_id == course_id)
    )
    assignments = result.all()

    if not assignments:
        return {"obtained": 0, "total": 0, "percentage": 0}

    assignment_ids = [a.id for a in assignments]
    total_marks = sum(a.total_marks for a in assignments)

    # 2. Get marks obtained by student
    result = await db.execute(
        select(func.sum(AssignmentSubmission.marks_obtained))
        .where(
            AssignmentSubmission.assignment_id.in_(assignment_ids),
            AssignmentSubmission.student_id == student_id
        )
    )
    obtained_marks = result.scalar() or 0

    percentage = round((obtained_marks / total_marks) * 100, 2) if total_marks else 0

    return {
        "obtained": obtained_marks,
        "total": total_marks,
        "percentage": percentage
    }


async def get_quiz_performance(course_id: UUID, student_id: UUID, db: AsyncSession):
    # 1. Get all quizzes in the course
    result = await db.execute(
        select(Quiz.id, Quiz.total_marks)
        .where(Quiz.course_id == course_id)
    )
    quizzes = result.all()

    if not quizzes:
        return {"obtained": 0, "total": 0, "percentage": 0}

    quiz_ids = [q.id for q in quizzes]
    total_marks = sum(q.total_marks for q in quizzes)

    # 2. Get marks obtained by student
    result = await db.execute(
        select(func.sum(QuizSubmission.total_score))
        .where(
            QuizSubmission.quiz_id.in_(quiz_ids),
            QuizSubmission.student_id == student_id
        )
    )
    obtained_marks = result.scalar() or 0

    percentage = round((obtained_marks / total_marks) * 100, 2) if total_marks else 0

    return {
        "obtained": obtained_marks,
        "total": total_marks,
        "percentage": percentage
    }
