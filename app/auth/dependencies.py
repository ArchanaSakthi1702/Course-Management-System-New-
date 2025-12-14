from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.future import select 
from jose import JWTError
import uuid


from app.database import get_db 
from app.models import User,UserRole,course_students,Course
from app.auth.jwt import verify_token


bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current logged-in User from the JWT access token.
    Verifies the token, converts user_id to UUID, and fetches the User from DB.
    Raises 401 if token is invalid, expired, or user not found.
    """
    token = credentials.credentials
    try:
        payload = verify_token(token,expected_type="access")
        user_id_str: str = payload.get("user_id")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Convert string back to UUID
        user_id = uuid.UUID(user_id_str)

    except (JWTError, ValueError):  # ValueError for invalid UUID string
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user



async def is_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Allow only users with ADMIN role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this resource"
        )
    return current_user


async def is_teacher(current_user: User = Depends(get_current_user)) -> User:
    """
    Allow only users with INSTRUCTOR role.
    """
    if current_user.role != UserRole.INSTRUCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


async def is_student(current_user: User = Depends(get_current_user)) -> User:
    """
    Allow only users with STUDENT role.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource"
        )
    return current_user
