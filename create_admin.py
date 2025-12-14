import asyncio
import uuid
from getpass import getpass
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import User, UserRole
from app.auth.password_security import hash_password


async def create_admin_interactive():
    """
    Interactively create a new admin user in the database.
    """
    email = input("Enter admin email: ").strip()
    name = input("Enter admin name (optional): ").strip() or None
    password = getpass("Enter admin password: ").strip()
    password_confirm = getpass("Confirm password: ").strip()

    if password != password_confirm:
        print("Passwords do not match. Exiting.")
        return

    async with AsyncSessionLocal() as session:
        # Check if admin with same email exists
        existing_admin = await session.execute(
            User.__table__.select().where(User.email == email)
        )
        if existing_admin.scalar():
            print(f"Admin with email {email} already exists.")
            return

        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            role=UserRole.ADMIN,
            email=email,
            name=name,
            password_hash=hash_password(password)
        )
        session.add(admin_user)
        await session.commit()
        print(f"Admin created successfully: {email}")


if __name__ == "__main__":
    asyncio.run(create_admin_interactive())
