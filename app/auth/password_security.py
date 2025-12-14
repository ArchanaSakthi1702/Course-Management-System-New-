from passlib.context import CryptContext

# ---------------------------
# Password hashing context
# ---------------------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------------
# Hash a password
# ---------------------------
def hash_password(password: str) -> str:
    """
    Returns a securely hashed password using Argon2.
    """
    return pwd_context.hash(password)


# ---------------------------
# Verify password
# ---------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the hashed password.
    Returns True if match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
