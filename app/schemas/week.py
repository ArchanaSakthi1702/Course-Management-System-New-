from pydantic import BaseModel
from typing import Optional,List
from uuid import UUID

class WeekCreate(BaseModel):
    week_number: int
    title: str
    description: str | None = None

class CreateWeeksRequest(BaseModel):
    weeks: List[WeekCreate]

class WeekUpdate(BaseModel):
    id: Optional[str] = None           # for updating existing week
    week_number: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None

class UpdateWeeksRequest(BaseModel):
    weeks: list[WeekUpdate]

class WeekBulkDeleteRequest(BaseModel):
    week_ids: List[UUID]

class WeekLite(BaseModel):
    id: str