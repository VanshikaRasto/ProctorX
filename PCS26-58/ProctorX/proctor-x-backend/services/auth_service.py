# Import PyJWT for JWT token handling
import jwt  # Fixed: Import PyJWT correctly
# Import bcrypt for password hashing and verification
import bcrypt 
# Import JSON for file-based data storage
import json
# Import OS for file system operations
import os
# Import datetime utilities for token expiration and timestamps
from datetime import datetime, timedelta
# Import typing utilities for type hints
from typing import Optional, Dict, Any
# Import FastAPI components for HTTP exceptions and status codes
from fastapi import HTTPException, status
# Import user models for authentication operations
from models.user import User, UserCreate, UserRole, UserStatus
# Import UUID for generating unique user IDs
import uuid

# JWT Configuration - CHANGE IN PRODUCTION
SECRET_KEY = "your-secret-key-change-in-production"  # Should be environment variable in production
ALGORITHM = "HS256"  # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_HOURS = 24  # Token validity period

class AuthService:
    """
    Authentication service for user management and JWT token operations.
    
    This service handles user registration, authentication, token generation,
    and user data persistence using JSON file storage.
    """
    
    def __init__(self):
        """Initialize the authentication service."""
        self.users_file = "data/users/users.json"  # File path for user data storage
        self._ensure_users_file()  # Create users file if it doesn't exist

    def _ensure_users_file(self):
        """
        Ensure the users JSON file exists.
        Creates an empty JSON object if the file doesn't exist.
        """
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)

    def _load_users(self) -> Dict[str, Dict]:
        """
        Load user data from the JSON file.
        
        Returns:
            Dictionary of user data with user IDs as keys
        """
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except:
            # Return empty dict if file doesn't exist or is corrupted
            return {}

    def _save_users(self, users: Dict[str, Dict]):
        """
        Save user data to the JSON file.
        
        Args:
            users: Dictionary of user data to save
        """
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2, default=str)

    def _hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed: Hashed password to verify against
            
        Returns:
            True if password matches hash, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user in the system.
        
        Args:
            user_data: User creation data including username, email, password, etc.
            
        Returns:
            Created User object (without password hash)
            
        Raises:
            HTTPException: If user with email or username already exists
        """
        users = self._load_users()
        
        # Check if user already exists (by email or username)
        for user in users.values():
            if user['email'] == user_data.email or user['username'] == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email or username already exists"
                )

        # Create new user with unique ID
        user_id = str(uuid.uuid4())
        hashed_password = self._hash_password(user_data.password)
        
        new_user = {
            "id": user_id,
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "role": user_data.role.value,
            "status": UserStatus.ACTIVE.value,
            "password_hash": hashed_password,
            "branch": user_data.branch if hasattr(user_data, 'branch') else None,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        # Save user to file
        users[user_id] = new_user
        self._save_users(users)
        
        # Return user without password hash for security
        user_dict = new_user.copy()
        del user_dict['password_hash']
        user_dict['created_at'] = datetime.fromisoformat(user_dict['created_at'])
        # Ensure branch key exists for Pydantic model compatibility
        if 'branch' not in user_dict:
            user_dict['branch'] = None
        
        return User(**user_dict)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: User's username
            password: User's plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        users = self._load_users()
        
        # Find user by username
        for user_data in users.values():
            if user_data['username'] == username:
                # Verify password
                if self._verify_password(password, user_data['password_hash']):
                    # Update last login timestamp
                    user_data['last_login'] = datetime.now().isoformat()
                    self._save_users(users)
                    
                    # Return user without password hash
                    user_dict = user_data.copy()
                    del user_dict['password_hash']
                    user_dict['created_at'] = datetime.fromisoformat(user_dict['created_at'])
                    if user_dict['last_login']:
                        user_dict['last_login'] = datetime.fromisoformat(user_dict['last_login'])
                    if 'branch' not in user_dict:
                        user_dict['branch'] = None
                    
                    return User(**user_dict)
        return None

    def create_access_token(self, user: User) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user: User object to create token for
            
        Returns:
            JWT token string
        """
        # Set token expiration time
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        # Create token payload
        to_encode = {
            "sub": user.id,           # Subject (user ID)
            "username": user.username,
            "role": user.role.value,
            "exp": expire             # Expiration time
        }
        
        # Encode and return JWT token
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid, expired, or missing required fields
        """
        try:
            # Decode and verify token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            
            # Check if user ID is present
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by their ID.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            User object if found, None otherwise
        """
        users = self._load_users()
        
        if user_id in users:
            user_data = users[user_id].copy()
            # Remove sensitive data
            del user_data['password_hash']
            # Convert string dates back to datetime objects
            user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
            if user_data['last_login']:
                user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])
            # Ensure branch field exists
            if 'branch' not in user_data:
                user_data['branch'] = None
            return User(**user_data)
        
        return None

    def require_role(self, required_role: UserRole):
        """
        Create a role-based access control decorator.
        
        Args:
            required_role: The role required to access the resource
            
        Returns:
            Function that checks if the current user has the required role
        """
        def role_checker(current_user: User):
            if current_user.role != required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required role: {required_role.value}"
                )
            return current_user
        return role_checker

# Global auth service instance for use across the application
auth_service = AuthService()

# Dependency functions for FastAPI route protection

def verify_token(token: str = None):
    """
    FastAPI dependency to verify JWT token.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    return auth_service.verify_token(token)

def get_current_user(token_data: dict = None) -> User:
    """
    FastAPI dependency to get current user from token data.
    
    Args:
        token_data: Decoded JWT token payload
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token data is missing or user not found
    """
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Retrieve user from database using token subject (user ID)
    user = auth_service.get_user_by_id(token_data["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user