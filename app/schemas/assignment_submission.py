from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


#for students
class AssignmentSubmissionRead(BaseModel):
    id: UUID
    assignment_id: UUID
    student_id: UUID
    file_url: str
    submitted_at: datetime
    marks_obtained: Optional[int] = None
    feedback: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


#for teachers
class AssignmentSubmissionTeacherRead(BaseModel):
    id: UUID
    student_id: UUID
    file_url: str
    submitted_at: datetime
    marks_obtained: Optional[int]
    feedback: Optional[str]

    model_config = {
        "from_attributes": True
    }


class AssignmentSubmissionGrade(BaseModel):
    marks_obtained: Optional[int]
    feedback: Optional[str]


