import asyncio
from app.database import engine, Base

# Import all models so SQLAlchemy knows them
from app.models import User,Course,Media,Assignment,AssignmentSubmission,Quiz,QuizAnswer,QuizOption,QuizQuestion,QuizSubmission,course_students  # add other models as you create them

async def flush_database():
    async with engine.begin() as conn:
        print("⚠️ Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ All tables dropped successfully!")

        print("🚀 Recreating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables recreated successfully!")

if __name__ == "__main__":
    asyncio.run(flush_database())
