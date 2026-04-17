# routers/auth.py
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import UserCreate, UserLogin, Token, User
from services.auth_service import auth_service, get_current_user, verify_token

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user (student or examiner)"""
    try:
        user = auth_service.create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """Authenticate user and return JWT token"""
    user = auth_service.authenticate_user(
        user_credentials.username,
        user_credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    access_token = auth_service.create_access_token(user)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=24 * 3600,  # 24 hours in seconds
        user=user
    )

@router.get("/me", response_model=User)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get current user information"""
    token_data = verify_token(credentials.credentials)
    user = get_current_user(token_data)
    return user

@router.post("/verify-token")
async def verify_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verify if token is valid"""
    token_data = verify_token(credentials.credentials)
    return {
        "valid": True,
        "user_id": token_data["sub"],
        "role": token_data["role"],
        "expires": token_data["exp"]
    }

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user (client-side token removal)"""
    # In a stateless JWT system, logout is primarily handled client-side
    # by removing the token from storage
    return {"message": "Successfully logged out"}