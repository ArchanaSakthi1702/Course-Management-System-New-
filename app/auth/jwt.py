from datetime import datetime, timedelta
from typing import Optional
import os
import uuid
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


# ---------------------------
# Create access token
# ---------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a short-lived JWT access token.

    Parameters:
        data (dict): Dictionary containing user info (e.g., user_id, role)
                     user_id should be converted to string if UUID.
        expires_delta (timedelta, optional): Custom expiration time. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# Create refresh token
# ---------------------------
def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a long-lived JWT refresh token.

    Parameters:
        data (dict): Dictionary containing user info (e.g., user_id, role)
                     user_id should be converted to string if UUID.
        expires_delta (timedelta, optional): Custom expiration time. Defaults to REFRESH_TOKEN_EXPIRE_DAYS.

    Returns:
        str: Encoded JWT refresh token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------
# Verify token
# ---------------------------
def verify_token(token: str, expected_type: str = "access") -> dict:
    """
    Verify a JWT token and return its payload.

    Parameters:
        token (str): JWT token string.
        expected_type (str): Token type to verify ("access" or "refresh"). Defaults to "access".

    Returns:
        dict: Decoded token payload.

    Raises:
        JWTError: If token is invalid, expired, or type mismatch.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise JWTError(f"Invalid token type. Expected '{expected_type}'.")
        return payload
    except JWTError as e:
        raise JWTError("Invalid or expired token") from e
