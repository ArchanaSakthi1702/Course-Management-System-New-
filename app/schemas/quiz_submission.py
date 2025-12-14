from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

#for students
class QuizAnswerSubmit(BaseModel):
    question_id: UUID
    selected_option_id: Optional[UUID]


class QuizSubmitRequest(BaseModel):
    answers: List[QuizAnswerSubmit]

class QuizSubmitResponse(BaseModel):
    submission_id: UUID
    quiz_id: UUID
    total_score: int

#for teachers
class QuizSubmissionListItem(BaseModel):
    submission_id: UUID
    quiz_id: UUID
    student_id: UUID
    student_roll_number: Optional[str]
    total_score: Optional[int]
    submitted_at: datetime

    model_config = {"from_attributes": True}


class QuizOptionResult(BaseModel):
    id: UUID
    option_text: str
    is_correct: bool

class QuizQuestionResult(BaseModel):
    id: UUID
    question_text: str
    marks: int
    selected_option: Optional[QuizOptionResult]
    correct_option: QuizOptionResult
    is_correct: bool


class QuizSubmissionDetailView(BaseModel):
    submission_id: UUID
    quiz_id: UUID
    quiz_title: str
    student_id: UUID
    student_roll_number: Optional[str]
    submitted_at: datetime
    total_score: int
    questions: list[QuizQuestionResult]

    model_config = {"from_attributes": True}

