from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials, HTTPBearer
from backend.authentication import schemas, utils, security
import uuid

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["authentication"])

# Register
@router.post('/register', response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: schemas.UserCreate):
    # Check duplicates
    exists, message = utils.user_exists(user.username, user.email)
    if exists:
        raise HTTPException(status_code=400, detail=message)
    
    new_user = {
        "user_id": str(uuid.uuid4()),
        "username": user.username,
        "email": user.email,
        "hashed_password": security.hash_password(user.password),
        "role": user.role.value,
        "status": schemas.UserStatus.ACTIVE.value,
        "movies_reviewed": [],
        "watch_later": [],
        "penalties": [],
    }

    # Save user to users_active.json
    utils.add_user(new_user, active=True)

    return {
        "user_id": new_user["user_id"],
        "username": new_user["username"],
        "email": new_user["email"],
        "role": new_user["role"],
        "status": new_user["status"],
    }

# Login
@router.post('/login', response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = utils.get_user_by_username(form_data.username)
    if not user or not security.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    if user["status"] != schemas.UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = security.create_access_token(
        data={"sub": user["user_id"], "role": user["role"], "status": user["status"]}
    )

    return {"access_token": access_token, "token_type": "bearer"}

# Logout
@router.post('/logout')
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    security.revoke_token(token)
    return {"message": "Successfully logged out and token revoked."}

# Refresh
@router.post("/refresh", response_model=schemas.Token)
async def refresh_token(current_user: schemas.TokenData = Depends(security.get_current_user)):
    new_token = security.create_access_token(
        data={"sub": current_user.user_id, "role": current_user.role, "status": current_user.status}
    )
    return {"access_token": new_token, "token_type": "bearer"}

# Who Am I
@router.get("/whoami", response_model=schemas.TokenData)
async def whoami(current_user=Depends(security.get_current_user)):
    return current_user


# REQUEST PASSWORD RESET
@router.post("/password/request")
async def request_password_reset(email: str):
    users = utils.load_all_users()
    user = next((u for u in users if u["email"] == email), None)
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    reset_token = security.create_reset_token(user["user_id"])

    # Normally you'd email this token. For dev/demo, just return it:
    return {"reset_token": reset_token, "message": "Use this token to reset password within 10 minutes"}

# CONFIRM PASSWORD RESET
@router.post("/password/reset")
async def reset_password(token: str, new_password: str):
    user_id = security.verify_reset_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Update user's hashed password
    users = utils.load_all_users()
    updated = False
    for user in users:
        if user["user_id"] == user_id:
            user["hashed_password"] = security.hash_password(new_password)
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    # Save to correct file
    active = [u for u in users if u["status"] == "active"]
    inactive = [u for u in users if u["status"] == "inactive"]
    utils.save_active_users(active)
    utils.save_inactive_users(inactive)

    return {"message": "Password successfully reset"}
