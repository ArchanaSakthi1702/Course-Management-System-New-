from pydantic import BaseModel
from typing import Optional,List
from datetime import datetime
from uuid import UUID

"""class QuizRead(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    total_marks: int
    time_limit_minutes: Optional[int] = None
    question_count: Optional[int] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

"""

class QuizLite(BaseModel):
    id: str
    title: str
    total_marks: int
    description: Optional[str]
    time_limit_minutes: Optional[int]
    no_of_questions: int


class QuizOptionCreate(BaseModel):
    option_text: str
    is_correct: bool = False


class QuizQuestionCreate(BaseModel):
    question_text: str
    marks: int = 1
    options: List[QuizOptionCreate]


class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    total_marks: int = 100
    time_limit_minutes: Optional[int] = None
    week_id: Optional[UUID] = None
    questions: List[QuizQuestionCreate]

class QuizCreateResponse(BaseModel):
    id: UUID
    title: str
    total_marks: int
    question_count: int

    model_config = {"from_attributes": True}

class QuizUpdate(QuizCreate):
    pass


#Listing Quiz and its questions to the users

class QuizOptionView(BaseModel):
    id: UUID
    option_text: str
    is_correct:Optional[bool]=None


class QuizQuestionView(BaseModel):
    id: UUID
    question_text: str
    marks: int
    options: List[QuizOptionView]


class WeekInfo(BaseModel):
    week_number: int
    title: str


class QuizDetailView(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    total_marks: int
    time_limit_minutes: Optional[int]
    week: Optional[WeekInfo]
    questions: List[QuizQuestionView]
