import os
import time
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_TTL = int(os.getenv("JWT_TTL_SECONDS", str(24 * 3600)))

bearer = HTTPBearer()


def create_token(project_id: str) -> str:
    payload = {
        "sub": project_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_project(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    payload = decode_token(credentials.credentials)
    return payload["sub"]
