# Import Pydantic components for data validation and serialization
from pydantic import BaseModel, EmailStr
# Import Enum for creating enumerated types
from enum import Enum
# Import typing utilities for optional and list type hints
from typing import Optional, List
# Import datetime for timestamp handling
from datetime import datetime

# User role enumeration - defines the different types of users in the system
class UserRole(str, Enum):
    STUDENT = "student"    # Regular student who takes exams
    EXAMINER = "examiner"  # Teacher/admin who creates and manages exams

# User status enumeration - represents the current state of a user account
class UserStatus(str, Enum):
    ACTIVE = "active"       # User can access the system normally
    INACTIVE = "inactive"   # User account is temporarily disabled
    SUSPENDED = "suspended" # User account is suspended due to violations

# Main User model - represents a user in the system with all essential information
class User(BaseModel):
    id: str                              # Unique identifier for the user
    email: EmailStr                      # User's email address (validated format)
    username: str                        # Unique username for login
    full_name: str                       # User's full display name
    role: UserRole                       # User's role (student or examiner)
    status: UserStatus                   # Current account status
    branch: Optional[str] = None         # Academic department/branch (optional)
    created_at: datetime                  # When the user account was created
    last_login: Optional[datetime] = None # Last time the user logged in

# User creation model - used when registering new users
class UserCreate(BaseModel):
    email: EmailStr      # User's email address
    username: str        # Desired username
    full_name: str       # User's full name
    password: str        # User's password (will be hashed)
    role: UserRole       # User's role in the system
    branch: Optional[str] = None  # Academic department/branch

# User login model - used for authentication requests
class UserLogin(BaseModel):
    username: str  # Username for authentication
    password: str  # Password for authentication

# Token response model - returned after successful authentication
class Token(BaseModel):
    access_token: str  # JWT token for authenticated requests
    token_type: str    # Type of token (usually "Bearer")
    expires_in: int    # Token expiration time in seconds
    user: User         # User information associated with the token