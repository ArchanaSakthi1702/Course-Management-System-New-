from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select


from app.database import get_db
from app.models import User,UserRole
from app.auth.jwt import create_access_token,create_refresh_token
from app.auth.password_security import verify_password
from app.schemas.user import TokenResponse
from app.schemas.admin_login import AdminLoginRequest


router=APIRouter(
    tags=["Admin Login"],
    prefix="/admin"
)

# ---------------------------
# Admin login route
# ---------------------------
@router.post("/login", response_model=TokenResponse)
async def admin_login(request: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate an admin using email and password.
    Returns access and refresh JWT tokens on success.
    Raises 401 if credentials are invalid.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    admin = result.scalars().first()

    if not admin or admin.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Update last login
    admin.last_login = datetime.utcnow()
    db.add(admin)
    await db.commit()

    # Generate tokens
    access_token = create_access_token({"user_id": str(admin.id), "role": admin.role.value})
    refresh_token = create_refresh_token({"user_id": str(admin.id), "role": admin.role.value})

    return TokenResponse(
        access_token=access_token, 
        refresh_token=refresh_token,
        role=admin.role.value
        )
