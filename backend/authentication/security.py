import os
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.authentication import schemas
from backend.authentication import utils

# BEARER TOKEN SCHEME (Extracts token from Authorization header)
security_scheme = HTTPBearer()

# Token Expiration Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Tokens expire after 60 minutes

# Secret Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")  # 🗝️ Get from env or use fallback
ALGORITHM = "HS256"  # JWT signing algorithm

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password Hashing
def hash_password(password: str) -> str:
    return pwd_context.hash(password)  # Convert plain text to secure hash

# Password Verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)  # ✅ Check if password matches hash

# Access Token Creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Set token expiration
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({ 
        "exp": expire,  # Add expiration timestamp
    })
    # 🔏 Encode JWT with secret key
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Token Verification
def verify_access_token(token: str) -> Optional[dict]:
    # Check blacklist first
    if is_token_revoked(token):
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            return None
        return payload
    except jwt.PyJWTError:
        return None
    
def cleanup_revoked_tokens():
    """Remove expired tokens from the revocation list."""
    tokens = utils.load_revoked_tokens()
    active_tokens = []
    for t in tokens:
        try:
            payload = jwt.decode(t, SECRET_KEY, algorithms=[ALGORITHM])
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            if exp > datetime.now(timezone.utc):
                active_tokens.append(t)
        except jwt.ExpiredSignatureError:
            continue  # Token already expired
        except Exception:
            continue
    utils.save_revoked_tokens(active_tokens)

def revoke_token(token: str):
    cleanup_revoked_tokens()
    tokens = utils.load_revoked_tokens()
    if token not in tokens:
        tokens.append(token)
    utils.save_revoked_tokens(tokens)

def is_token_revoked(token: str) -> bool:
    return token in utils.load_revoked_tokens()

# Create password reset token
def create_reset_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {"sub": user_id, "scope": "password_reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Verify reset token
def verify_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "password_reset":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# CURRENT USER EXTRACTION PROCESS (Dependency)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 🆕 Check if account is active
    if payload.get("status") != schemas.UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # ✅ Return user data from token
    return schemas.TokenData(user_id=payload["sub"], role=payload["role"], status=payload["status"])

