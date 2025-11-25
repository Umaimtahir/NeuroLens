from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
from encryption import EncryptionService
from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        is_guest: bool = payload.get("is_guest", False)
        
        if username is None:
            raise credentials_exception
        
        # Handle guest users
        if is_guest:
            # Return a mock user for guest
            from models import User as UserModel
            guest_user = UserModel(
                id=0,
                name="Guest User",
                email_encrypted="",
                username_hash="",
                username_encrypted="",
                password_hash="",
                is_active=True
            )
            return guest_user
        
    except JWTError:
        raise credentials_exception
    
    # Find real user using hash
    username_hash = EncryptionService.hash_username(username)
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if user is None:
        raise credentials_exception
    
    return user