from fastapi import APIRouter, Depends, HTTPException,Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models import Course, Assignment, User,CourseWeek
from app.database import get_db
from app.auth.dependencies import is_teacher
from app.schemas.assignment import AssignmentCreate,AssignmentLite,AssignmentBulkDelete,AssignmentUpdate
from app.helpers.file_paths import delete_assignment_file_safely

router = APIRouter(
    prefix="/teacher/assignment",
    tags=["Teacher Assignment Endpoints"]
)

@router.post("/create-assignment/{course_id}", status_code=201)
async def create_assignment(
    course_id: UUID,
    assignment_in: AssignmentCreate,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # --------------------------
    # Fetch the course
    # --------------------------
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Instructor validation
    if current_user.id != course.instructor_id:
        raise HTTPException(
            status_code=403, 
            detail="Only the course instructor can create assignments"
        )

    # --------------------------
    # OPTIONAL WEEK VALIDATION
    # --------------------------
    week_id = assignment_in.week_id if hasattr(assignment_in, "week_id") else None

    if week_id:
        result_week = await db.execute(
            select(CourseWeek).where(CourseWeek.id == week_id)
        )
        week = result_week.scalar_one_or_none()

        if not week:
            raise HTTPException(404, "Week not found")

        if week.course_id != course.id:
            raise HTTPException(
                400,
                "This week does not belong to the selected course"
            )
    else:
        week_id = None  # Global assignment

    # --------------------------
    # Create assignment
    # --------------------------
    new_assignment = Assignment(
        course_id=course.id,
        instructor_id=current_user.id,
        title=assignment_in.title,
        description=assignment_in.description,
        total_marks=assignment_in.total_marks,
        deadline=assignment_in.deadline,
        week_id=week_id
    )

    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)

    return {
        "id": str(new_assignment.id),
        "title": new_assignment.title,
        "description": new_assignment.description,
        "total_marks": new_assignment.total_marks,
        "deadline": new_assignment.deadline,
        "week_id": str(new_assignment.week_id) if new_assignment.week_id else None,
        "course_id": str(new_assignment.course_id),
        "created_at": new_assignment.created_at,
        "updated_at": new_assignment.updated_at
    }


@router.put("/update-assignment/{assignment_id}", response_model=AssignmentLite)
async def update_assignment(
    assignment_id: UUID,
    assignment_in: AssignmentUpdate,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    # Fetch assignment
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    # Only course instructor can update
    if assignment.instructor_id != current_user.id:
        raise HTTPException(403, "You cannot update this assignment")

    # Update normal fields (only if provided)
    if assignment_in.title is not None:
        assignment.title = assignment_in.title

    if assignment_in.description is not None:
        assignment.description = assignment_in.description

    if assignment_in.total_marks is not None:
        assignment.total_marks = assignment_in.total_marks

    if assignment_in.deadline is not None:
        assignment.deadline = assignment_in.deadline

    # ------------------------------
    # OPTIONAL WEEK UPDATE
    # ------------------------------
    if assignment_in.week_id is not None:
        # Check if week exists
        result_week = await db.execute(
            select(CourseWeek).where(CourseWeek.id == assignment_in.week_id)
        )
        week = result_week.scalar_one_or_none()
        if not week:
            raise HTTPException(404, "Week not found")

        # Check if week belongs to the same course as the assignment
        if week.course_id != assignment.course_id:
            raise HTTPException(
                400,
                "This week does not belong to the same course as the assignment"
            )

        # Update week
        assignment.week_id = assignment_in.week_id

    # Save changes
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return AssignmentLite(
        id=str(assignment.id),
        title=assignment.title,
        deadline=assignment.deadline,
        total_marks=assignment.total_marks,
        description=assignment.description,
    )


@router.delete("/delete-assignment/{assignment_id}", status_code=204)
async def delete_global_assignment(
    assignment_id: UUID,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(selectinload(Assignment.submissions))
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(404, "Assignment not found")

    if assignment.instructor_id != current_user.id:
        raise HTTPException(403, "Only the course instructor can delete this assignment")
    
    for submission in assignment.submissions:
        delete_assignment_file_safely(submission.file_url)

    await db.delete(assignment)
    await db.commit()
    return {"detail": "Assignment deleted successfully"}


@router.post("/bulk-delete", status_code=204)
async def bulk_delete_assignments(
    payload: AssignmentBulkDelete,
    current_user: User = Depends(is_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Assignment)
        .where(Assignment.id.in_(payload.assignment_ids))
        .options(selectinload(Assignment.submissions))
    )
    assignments = result.scalars().all()

    if not assignments:
        raise HTTPException(404, "No assignments found for the given IDs")

    # Ensure all assignments belong to instructor
    for assignment in assignments:
        if assignment.instructor_id != current_user.id:
            raise HTTPException(403, "You can only delete your own assignments")

    for assignment in assignments:
        for submission in assignment.submissions:
            delete_assignment_file_safely(submission.file_url)
        await db.delete(assignment)
    await db.commit()
    return {"detail": f"{len(assignments)} assignments deleted successfully"}

