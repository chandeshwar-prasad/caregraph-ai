import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import bcrypt
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

# Environment & JWT Configurations
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
JWT_SECRET = os.getenv("JWT_SECRET")

INSECURE_DEV_SECRETS = {
    "default_secret_key_if_none_set_in_env_file_12345",
    "YOUR_32_BYTE_HEX_JWT_SECRET_KEY",
    "secret",
    "changeme",
    "password"
}

if ENVIRONMENT == "production":
    if not JWT_SECRET or JWT_SECRET in INSECURE_DEV_SECRETS or len(JWT_SECRET) < 32:
        raise ValueError(
            "CRITICAL SECURITY ERROR: In production environment, a high-entropy JWT_SECRET "
            "(minimum 32 characters, non-default) must be explicitly configured."
        )
else:
    if not JWT_SECRET:
        JWT_SECRET = "default_secret_key_if_none_set_in_env_file_12345"

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Hashing utility
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False

# Token generation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# Dependency injection for user authentication
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username, role=role)
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

# Helper dependency to enforce role constraints
class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for current user role"
            )
        return current_user

require_role = lambda role: RoleChecker([role])
