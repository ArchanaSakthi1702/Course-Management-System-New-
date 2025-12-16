from pydantic import BaseModel

class CategoryItem(BaseModel):
    id: str
    name: str