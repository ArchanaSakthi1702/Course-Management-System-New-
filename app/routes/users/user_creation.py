from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.auth.password_security import hash_password

router = APIRouter(prefix="/user", tags=["User Registration"])


@router.post("/register")
async def register_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Validate required fields based on role
    if data.role in [UserRole.STUDENT, UserRole.INSTRUCTOR] and not data.roll_number:
        raise HTTPException(400, "roll_number is required for students and instructors")

    if data.role == UserRole.ADMIN and not data.email:
        raise HTTPException(400, "email is required for admin users")

    # Check if roll number exists (students + instructors)
    if data.roll_number:
        result = await db.execute(select(User).where(User.roll_number == data.roll_number))
        if result.scalars().first():
            raise HTTPException(400, "Roll number already exists")

    # Check if email exists (admins)
    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalars().first():
            raise HTTPException(400, "Email already exists")

    user = User(
        role=data.role,
        name=data.name,
        email=data.email,
        roll_number=data.roll_number,
        password_hash=hash_password(data.password),

        # Student fields
        department=data.department,
        year=data.year,
        section=data.section,
        dob=data.dob,
        mobile=data.mobile,

        # Instructor fields
        qualification=data.qualification,
        experience_years=data.experience_years,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "message": "User registered successfully",
        "user_id": str(user.id),
        "role": user.role,
    }
