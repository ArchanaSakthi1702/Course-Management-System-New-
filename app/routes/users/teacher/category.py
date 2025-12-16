from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete,func
from typing import List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth.dependencies import is_teacher,get_current_user
from app.models import CourseCategory,CourseWeek,Course,User
from app.schemas.course import CourseBasicItem,StudentCoursesCursorResponse
from app.schemas.category import CategoryItem

router = APIRouter(
    prefix="/teacher/categories", 
    tags=["Teacher Course Categories Endpoints"],
    dependencies=[Depends(is_teacher)]
    )

@router.post("/create-category", status_code=201)
async def create_category(
    name: str = Body(..., embed=True),
    description: str | None = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness
    existing = await db.execute(
        select(CourseCategory).where(CourseCategory.name == name)
    )
    if existing.scalars().first():
        raise HTTPException(400, "Category already exists")

    category = CourseCategory(
        name=name.strip(),
        description=description
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return {
        "message": "Category created successfully",
        "category_id": str(category.id)
    }


@router.patch("/update/{category_id}")
async def update_category(
    category_id: UUID,
    name: str | None = Body(None, embed=True),
    description: str | None = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(404, "Category not found")

    if name and name != category.name:
        existing = await db.execute(
            select(CourseCategory).where(CourseCategory.name == name)
        )
        if existing.scalars().first():
            raise HTTPException(400, "Category name already exists")
        category.name = name.strip()

    if description is not None:
        category.description = description

    await db.commit()
    await db.refresh(category)

    return {
        "message": "Category updated successfully",
        "category_id": str(category.id)
    }


@router.delete("/delete/{category_id}")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CourseCategory).where(CourseCategory.id == category_id)
    )
    category = result.scalars().first()

    if not category:
        raise HTTPException(404, "Category not found")

    await db.delete(category)
    await db.commit()

    return {
        "message": "Category deleted successfully",
        "category_id": str(category_id)
    }


@router.delete("/bulk-delete")
async def bulk_delete_categories(
    category_ids: List[UUID] = Body(...),
    db: AsyncSession = Depends(get_db),
):
    if not category_ids:
        raise HTTPException(400, "No category IDs provided")

    result = await db.execute(
        delete(CourseCategory)
        .where(CourseCategory.id.in_(category_ids))
        .returning(CourseCategory.id)
    )

    deleted_ids = result.scalars().all()

    if not deleted_ids:
        raise HTTPException(404, "No categories found to delete")

    await db.commit()

    return {
        "message": "Categories deleted successfully",
        "deleted_count": len(deleted_ids),
        "deleted_ids": [str(cid) for cid in deleted_ids]
    }

@router.get("/list-categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CourseCategory)
        .order_by(CourseCategory.name.asc())
    )
    categories = result.scalars().all()

    return {
        "count": len(categories),
        "data": [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "created_at": c.created_at
            }
            for c in categories
        ]
    }


@router.get(
    "/get-courses-in-category/{category_id}",
    response_model=StudentCoursesCursorResponse
)
async def list_courses_by_category(
    category_id: UUID,
    cursor: str | None = Query(None, description="Cursor timestamp"),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cursor_time = None
    if cursor:
        try:
            cursor_time = datetime.fromisoformat(cursor)
        except Exception:
            raise HTTPException(400, "Invalid cursor timestamp")
    query = (
        select(Course)
        .join(Course.categories)
        .where(CourseCategory.id == category_id)
        .options(selectinload(Course.categories))
    )

    if cursor_time:
        query = query.where(Course.created_at < cursor_time)

    query = query.order_by(
        Course.created_at.desc(),
        Course.id.desc()
    ).limit(limit + 1)

    result = await db.execute(query)
    courses = result.scalars().all()
    if len(courses) > limit:
        next_cursor = courses[limit-1].created_at.isoformat()
        courses = courses[:limit]
    else:
        next_cursor = None


    course_ids = [c.id for c in courses]
    week_count_map = {}

    if course_ids:
        week_rows = await db.execute(
            select(
                CourseWeek.course_id,
                func.count(CourseWeek.id)
            )
            .where(CourseWeek.course_id.in_(course_ids))
            .group_by(CourseWeek.course_id)
        )
        week_count_map = {str(r[0]): r[1] for r in week_rows.all()}

    return StudentCoursesCursorResponse(
        limit=limit,
        next_cursor=next_cursor,
        data=[
            CourseBasicItem(
                id=str(c.id),
                code=c.code,
                name=c.name,
                description=c.description,
                thumbnail=c.thumbnail,
                credits=c.credits,
                number_of_weeks=week_count_map.get(str(c.id), 0),
                categories=[
                    CategoryItem(
                        id=str(cat.id),
                        name=cat.name
                    )
                    for cat in c.categories
                ]
            )
            for c in courses
        ]
    )
