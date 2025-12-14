from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.database import get_db
from app.models import User, UserRole
from app.auth.password_security import verify_password
from app.auth.jwt import create_access_token, create_refresh_token
from app.schemas.user import TokenResponse,UserLoginRequest

router = APIRouter(tags=["User Login"])


# ---------------------------
# User login route (student/instructor)
# ---------------------------
@router.post("/user/login", response_model=TokenResponse)
async def user_login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a student or instructor using roll_number and password.
    Returns access and refresh JWT tokens on success.
    Raises 401 if credentials are invalid.
    """
    result = await db.execute(select(User).where(User.roll_number == request.roll_number))
    user = result.scalars().first()

    if not user or user.role not in [UserRole.STUDENT, UserRole.INSTRUCTOR]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid roll number or password"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid roll number or password"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.add(user)
    await db.commit()

    # Generate tokens
    access_token = create_access_token({"user_id": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"user_id": str(user.id), "role": user.role.value})

    return TokenResponse(
        access_token=access_token, 
        refresh_token=refresh_token,
        role=user.role.value
        )