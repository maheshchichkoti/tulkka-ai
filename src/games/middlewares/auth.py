# src/middlewares/auth.py
from fastapi import Header, HTTPException, Depends
from typing import Optional
from src.security import decode_jwt
from src.config import settings

def get_current_user(authorization: Optional[str] = Header(None)):
    # Development mode bypass for testing
    if settings.ENVIRONMENT == "development":
        if not authorization:
            # Return test user in dev mode
            return {"userId": "test-user-123", "claims": {"sub": "test-user-123", "role": "user"}}
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_jwt(token)
    if not payload or 'sub' not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Expect 'sub' as user id
    return {"userId": payload.get("sub"), "claims": payload}
