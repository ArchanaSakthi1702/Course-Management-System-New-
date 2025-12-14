import asyncio
from app.database import engine, Base

# Import all models here so SQLAlchemy knows them
from app.models import User,Course,Media,Assignment,AssignmentSubmission,Quiz,QuizAnswer,QuizOption,QuizQuestion,QuizSubmission,course_students  # add other models as you create them



async def create_tables():
    async with engine.begin() as conn:
        print("🚀 Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
