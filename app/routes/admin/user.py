from fastapi import APIRouter,Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.auth.dependencies import is_admin
from app.schemas.user import UserListBasic

router=APIRouter(
    prefix="/admin",
    tags=["Admin User Endpoints"],
    dependencies=[Depends(is_admin)]
)


@router.get("/list-users", response_model=List[UserListBasic])
async def list_all_users(
    db: AsyncSession = Depends(get_db)
):

    # Fetch only required columns → faster & cleaner
    result = await db.execute(
        select(User.id, User.name, User.roll_number, User.role)
    )

    users = result.all()

    # Convert SQLAlchemy row objects to Pydantic models
    return [
        UserListBasic(
            id=str(u.id),
            name=u.name,
            roll_number=u.roll_number,
            role=u.role
        ) for u in users
    ]
