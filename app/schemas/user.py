from pydantic import BaseModel,EmailStr
from typing import Optional
from datetime import datetime,date
from uuid import UUID
from app.models import UserRole


class UserCreate(BaseModel):
    role: UserRole
    name: str
    email: Optional[EmailStr] = None
    roll_number: Optional[str] = None
    password: str

    # Student fields
    department: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None
    dob: Optional[str] = None
    mobile: Optional[str] = None

    # Instructor fields
    qualification: Optional[str] = None
    experience_years: Optional[int] = None


class UserLoginRequest(BaseModel):
    roll_number: str
    password: str



class UserProfile(BaseModel):
    id: UUID
    role: str
    name: str
    email: Optional[str]
    roll_number: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    profile_pic: Optional[str]

    # Student-specific
    department: Optional[str]
    year: Optional[str]
    section: Optional[str]
    dob: Optional[date]
    mobile: Optional[str]

    # Instructor-specific
    qualification: Optional[str]
    experience_years: Optional[int]

    model_config={
        "from_attributes":True
    }


class TokenResponse(BaseModel):

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role:str



#for admin

class UserListBasic(BaseModel):
    id: str
    name: str
    roll_number: str | None
    role: UserRole

    model_config = {
        "from_attributes": True
    }
