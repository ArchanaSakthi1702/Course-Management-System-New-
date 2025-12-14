from pydantic import BaseModel, Field
from uuid import UUID


class MediaProgressUpdate(BaseModel):
    media_id: UUID
    watched_seconds: int = Field(..., ge=0)

    model_config = {"from_attributes": True}


class MediaProgressResponse(BaseModel):
    media_id: UUID
    watched_seconds: int
    is_completed: bool
