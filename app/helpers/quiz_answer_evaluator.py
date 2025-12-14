from typing import  List,Dict
from uuid import UUID

from app.schemas.quiz_submission import QuizAnswerSubmit
from app.models import Quiz, QuizAnswer,QuizQuestion


def evaluate_quiz_answers(
    quiz: Quiz,
    submission_id: UUID,
    answers_payload:List[QuizAnswerSubmit]
):
    """
    Evaluates quiz answers and returns:
    - total_score
    - list of QuizAnswer ORM objects
    """

    total_score = 0
    answer_rows: List[QuizAnswer] = []

    # Map questions for fast lookup
    question_map:Dict[UUID,QuizQuestion] = {q.id: q for q in quiz.questions}

    for ans in answers_payload:
        question = question_map.get(ans.question_id)
        if not question:
            continue

        selected_option = None
        is_correct = False
    
        for opt in question.options:
            if opt.id == ans.selected_option_id:
                selected_option = opt
                is_correct = opt.is_correct
                break

        if is_correct:
            total_score += question.marks

        answer_rows.append(
            QuizAnswer(
                submission_id=submission_id,
                question_id=question.id,
                selected_option_id=selected_option.id if selected_option else None,
            )
        )

    return total_score, answer_rows
