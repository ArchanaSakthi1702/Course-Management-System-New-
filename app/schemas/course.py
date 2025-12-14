from pydantic import BaseModel
from typing import Optional,List
from uuid import UUID
from datetime import datetime


from app.schemas.media import MediaLite
from app.schemas.assignment import AssignmentLite
from app.schemas.quiz import QuizLite
from app.schemas.week import WeekUpdate,WeekLite

#For Teachers 
class CourseItem(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    thumbnail:Optional[str]=None
    credits: Optional[int]
    created_at: datetime
    updated_at: datetime


class CourseCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    credits: Optional[int] = None


class CourseUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    credits: Optional[int] = None

class CourseBulkDelete(BaseModel):
    course_ids: List[str]



class MyCoursesCursorResponse(BaseModel):
    teacher_id: str
    limit: int
    next_cursor: Optional[str]
    data: List[CourseItem]


#For Students and Teachers 
class CourseBasicItem(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    thumbnail: Optional[str] = None
    credits: Optional[int]

    number_of_weeks: Optional[int]=None          # ⬅️ NEW

class StudentCoursesCursorResponse(BaseModel):
    limit: int
    next_cursor: Optional[str]
    data: List[CourseBasicItem]


class EnrollmentResponse(BaseModel):
    message: str
    course_id: str
    student_id: str

#Response for enrolled and teacher of the course
class CourseDetailResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    credits: Optional[int]
    thumbnail: Optional[str]

    instructor_name: Optional[str]
    instructor_id: str
    enrolled_count: int

    media_items: List[MediaLite] = []
    assignments: List[AssignmentLite] = []
    quizzes: List[QuizLite] = []
    weeks: List[WeekLite] = []

    created_at: datetime
    updated_at: datetime

    model_config={
        "from_attributes":True
    }


#For enrolled students


class StudentCourseListItem(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    credits: int | None
    thumbnail: str | None
    instructor_name: str | None

    model_config = {"from_attributes": True}


class StudentCourseListResponse(BaseModel):
    courses: list[StudentCourseListItem]
