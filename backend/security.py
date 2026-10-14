import os
import datetime
from typing import Optional, List
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db
import models

load_dotenv()

AUTH_SECRET = os.getenv("AUTH_SECRET", "career-os-super-secret-key-production-2026-vantage")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, AUTH_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def extract_token_from_request(request: Request) -> Optional[str]:
    """Extracts JWT token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1].strip()
    
    # Check cookies
    cookie_token = request.cookies.get("careeros_token")
    if cookie_token:
        return cookie_token.strip()
    
    return None

def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """Retrieves authenticated user if token is present, without raising 401."""
    token = extract_token_from_request(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    user_id = payload.get("sub")
    try:
        user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        return user
    except Exception:
        return None

def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    """Retrieves authenticated user from JWT token, raising 401 if missing/invalid."""
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )
    return user

def require_role(allowed_roles: List[str]):
    """Enforces role-based access control (STUDENT, COLLEGE, RECRUITER)."""
    normalized_allowed = [r.upper() for r in allowed_roles]
    # Map COLLEGE_ADMIN or COLLEGE to matching synonyms
    if "COLLEGE" in normalized_allowed and "COLLEGE_ADMIN" not in normalized_allowed:
        normalized_allowed.append("COLLEGE_ADMIN")
    if "COLLEGE_ADMIN" in normalized_allowed and "COLLEGE" not in normalized_allowed:
        normalized_allowed.append("COLLEGE")

    def role_checker(current_user: models.User = Depends(get_current_user)):
        user_role = (current_user.role or "").upper()
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}, current role: {current_user.role}",
            )
        return current_user
    return role_checker
