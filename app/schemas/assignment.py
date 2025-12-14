from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class AssignmentCreate(BaseModel):
    title: str
    description: str | None = None
    total_marks: int = 100
    deadline: datetime
    week_id: UUID | None = None   # Optional

"""
class AssignmentRead(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    total_marks: int
    deadline: datetime
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
    """

class AssignmentLite(BaseModel):
    id: str
    title: str
    deadline: datetime
    total_marks: int
    description: Optional[str]

class AssignmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    total_marks: int | None = None
    deadline: datetime | None = None
    week_id: UUID | None = None

class AssignmentBulkDelete(BaseModel):
    assignment_ids: list[UUID]

