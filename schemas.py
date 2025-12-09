from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re

class UserSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str
    
    @validator('name')
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if not re.match(r'^[a-zA-Z\s\'-]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        v = v.strip().lower()
        if not v:
            raise ValueError('Username cannot be empty')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError('Username can only contain lowercase letters, numbers, hyphens, and underscores')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 72:
            raise ValueError('Password must be less than 72 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3)
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    username: str
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class SignupResponse(BaseModel):
    token: str
    user: UserResponse
    message: str = "Account created successfully"


class InitiateSignupResponse(BaseModel):
    message: str = "Verification code sent to your email"
    email: str


class VerifySignupRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ReportData(BaseModel):
    date: str
    avgStress: float
    avgFocus: float


# Profile Update Schemas
class UpdateProfileRequest(BaseModel):
    """Request to update profile - sends verification if email changes"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @validator('name')
    def validate_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        if not re.match(r'^[a-zA-Z\s\'-]+$', v):
            raise ValueError('Name can only contain letters, spaces, hyphens, and apostrophes')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            raise ValueError('Username cannot be empty')
        if ' ' in v:
            raise ValueError('Username cannot contain spaces')
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError('Username can only contain lowercase letters, numbers, hyphens, and underscores')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v


class VerifyProfileUpdateRequest(BaseModel):
    """Verify email change with code"""
    code: str = Field(..., min_length=6, max_length=6)


class ChangePasswordRequest(BaseModel):
    """Change password (requires current password)"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 72:
            raise ValueError('Password must be less than 72 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Password Reset Schemas ONLY
class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    
    @validator('username')
    def validate_username(cls, v):
        return v.strip().lower()


class VerifyResetCodeRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    
    @validator('username')
    def validate_username(cls, v):
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    username: str = Field(..., min_length=3)
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str
    
    @validator('username')
    def validate_username(cls, v):
        return v.strip().lower()
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if len(v) > 72:
            raise ValueError('Password must be less than 72 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v