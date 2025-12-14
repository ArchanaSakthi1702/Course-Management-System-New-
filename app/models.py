import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum, Date, ForeignKey, Table, Text,UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


# ---------------------------
# Role Enum
# ---------------------------
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"
    INSTRUCTOR = "instructor"


# ---------------------------
# User Model
# ---------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    role = Column(Enum(UserRole, name="user_role_enum"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    roll_number = Column(String(50), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    profile_pic = Column(String(255), nullable=True)

    # Student-specific
    department = Column(String(100), nullable=True)
    year = Column(String(10), nullable=True)
    section = Column(String(10), nullable=True)
    dob = Column(Date, nullable=True)
    mobile = Column(String(20), nullable=True)

    # Instructor-specific
    qualification = Column(String(100), nullable=True)
    experience_years = Column(Integer, nullable=True)

    super_admin = Column(Boolean, default=False)


# ---------------------------
# Course Model
# ---------------------------
class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=True)
    
    thumbnail = Column(String(500), nullable=True)

    instructor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instructor = relationship("User", backref="courses_taught")

    students = relationship(
        "User",
        secondary="course_students",
        backref="enrolled_courses"
    )

    media_items = relationship("Media", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    weeks = relationship("CourseWeek", back_populates="course", cascade="all, delete-orphan")


# ---------------------------
# Association Table
# ---------------------------
course_students = Table(
    "course_students",
    Base.metadata,
    Column("course_id", UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True),
    Column("student_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
)


# ---------------------------
# Media Model
# ---------------------------
class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    week_id = Column(UUID(as_uuid=True), ForeignKey("course_weeks.id"), nullable=True)

    title = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    media_type = Column(String(50), nullable=False)
    duration_seconds = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="media_items")
    uploader = relationship("User")
    week = relationship("CourseWeek", back_populates="media_items")


class MediaProgress(Base):
    __tablename__ = "media_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    watched_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    media = relationship("Media")
    student = relationship("User")

    __table_args__ = (
        UniqueConstraint("media_id", "student_id", name="unique_media_progress"),
    )



class CourseWeek(Base):
    __tablename__ = "course_weeks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)

    week_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("Course", back_populates="weeks")
    media_items = relationship("Media", back_populates="week")
    assignments = relationship("Assignment", back_populates="week")
    quizzes = relationship("Quiz", back_populates="week")

# ---------------------------
# Assignment Model
# ---------------------------
class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    instructor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    total_marks = Column(Integer, default=100)
    deadline = Column(DateTime(timezone=True), nullable=False)

    week_id = Column(UUID(as_uuid=True), ForeignKey("course_weeks.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="assignments")
    instructor = relationship("User")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")
    week = relationship("CourseWeek", back_populates="assignments")



class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    file_url = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    marks_obtained = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User")


# ---------------------------
# Quiz Model
# ---------------------------
class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    instructor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    total_marks = Column(Integer, default=100)
    time_limit_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    week_id = Column(UUID(as_uuid=True), ForeignKey("course_weeks.id"), nullable=True)


    course = relationship("Course", back_populates="quizzes")
    instructor = relationship("User")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    submissions = relationship("QuizSubmission", back_populates="quiz", cascade="all, delete-orphan")
    week = relationship("CourseWeek", back_populates="quizzes")



class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)

    question_text = Column(Text, nullable=False)
    marks = Column(Integer, default=1)

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("QuizOption", back_populates="question", cascade="all, delete-orphan")


class QuizOption(Base):
    __tablename__ = "quiz_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id"), nullable=False)

    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("QuizQuestion", back_populates="options")


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    submitted_at = Column(DateTime, default=datetime.utcnow)
    total_score = Column(Integer, nullable=True)

    quiz = relationship("Quiz", back_populates="submissions")
    student = relationship("User")
    answers = relationship("QuizAnswer", back_populates="submission", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("quiz_submissions.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("quiz_questions.id"), nullable=False)
    selected_option_id = Column(UUID(as_uuid=True), ForeignKey("quiz_options.id"), nullable=True)

    submission = relationship("QuizSubmission", back_populates="answers")
    question = relationship("QuizQuestion")
    selected_option = relationship("QuizOption")
