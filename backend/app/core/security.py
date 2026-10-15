from datetime import datetime, timezone, timedelta
from typing import Any, Union
from jose import jwt
import bcrypt
import os

SECRET_KEY = os.getenv("SECRET_KEY", "graphguard_insecure_secret_key_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if isinstance(plain_password, str):
        plain_password_bytes = plain_password.encode("utf-8")
    else:
        plain_password_bytes = plain_password
    if isinstance(hashed_password, str):
        hashed_password_bytes = hashed_password.encode("utf-8")
    else:
        hashed_password_bytes = hashed_password
    try:
        return bcrypt.checkpw(plain_password_bytes[:72], hashed_password_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    if isinstance(password, str):
        password_bytes = password.encode("utf-8")
    else:
        password_bytes = password
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes[:72], salt).decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
