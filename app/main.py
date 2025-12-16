from fastapi import FastAPI

from app.routes.users.user_creation import router as user_registration_router
from app.routes.users.user_login import router as user_login_router
from app.routes.users.user_profile import router as user_profile_router
from app.routes.users.course import router as user_course_router
from app.routes.users.week import router as user_week_router

from app.routes.admin.admin_login import router as admin_login_router
from app.routes.admin.user import router as admin_user_router

from app.routes.users.teacher.course import router as teacher_course_router
from app.routes.users.teacher.week import router as teacher_weeks_router
from app.routes.users.teacher.media import router as teacher_media_router
from app.routes.users.teacher.assignment import router as teacher_assignment_router
from app.routes.users.teacher.assignment_submission import router as teacher_assignment_submission_router
from app.routes.users.teacher.quiz import router as teacher_quiz_router
from app.routes.users.teacher.quiz_submission import router as teacher_quiz_submission_router
from app.routes.users.teacher.category import router as teacher_category_router

from app.routes.users.student.course import router as student_course_router
from app.routes.users.student.assignment_submissions import router as student_assignment_router
from app.routes.users.student.quiz import router as student_quiz_router
from app.routes.users.student.quiz_submission import router as student_quiz_submission_router
from app.routes.users.student.media_progress import router as student_media_progress_router





app=FastAPI(
    title="Course Management System"
)

@app.get("/")
def root():
    return {
        "message":"Course Management System is Running!"
        }


app.include_router(user_registration_router)
app.include_router(user_login_router)
app.include_router(user_profile_router)
app.include_router(user_course_router)
app.include_router(user_week_router)

app.include_router(admin_login_router)
app.include_router(admin_user_router)

app.include_router(teacher_course_router)
app.include_router(teacher_media_router)
app.include_router(teacher_assignment_router)
app.include_router(teacher_assignment_submission_router)
app.include_router(teacher_weeks_router)
app.include_router(teacher_quiz_router)
app.include_router(teacher_quiz_submission_router)
app.include_router(teacher_category_router)

app.include_router(student_course_router)
app.include_router(student_assignment_router)
app.include_router(student_quiz_submission_router)
app.include_router(student_quiz_router)
app.include_router(student_media_progress_router)



