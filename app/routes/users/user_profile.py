from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User
from app.schemas.user import UserProfile
from app.auth.dependencies import get_current_user



router = APIRouter(prefix="/user", tags=["User Profile"])

@router.get("/my-profile", response_model=UserProfile)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user