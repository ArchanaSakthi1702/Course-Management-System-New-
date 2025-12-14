from pydantic import BaseModel
from typing import Optional

"""
class MediaRead(BaseModel):
    id: UUID
    title: str
    media_type: str
    file_url: str
    duration_seconds: Optional[int] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
"""
class MediaLite(BaseModel):
    id: str
    title: str
    file_url: str
    media_type: str
    duration_seconds:Optional[int]=None


class MediaBulkDelete(BaseModel):
    media_ids: list[str]  # list of media IDs to delete
