from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email_encrypted = Column(String, nullable=False)
    email_hash = Column(String, unique=True, nullable=False, index=True)
    username_hash = Column(String, unique=True, nullable=False, index=True)
    username_encrypted = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Email verification fields
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(6), nullable=True)
    verification_code_expiry = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    reset_token = Column(String(10), nullable=True)
    reset_token_expiry = Column(DateTime(timezone=True), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Current emotion state
    current_emotion = Column(String(50), nullable=True)
    current_emotion_intensity = Column(Float, nullable=True)


class EmotionLog(Base):
    """Store emotion detection history"""
    __tablename__ = "emotion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=False, index=True)
    emotion = Column(String(50), nullable=False)
    intensity = Column(Float, nullable=False)
    content_type = Column(String(50), nullable=True)
    content_confidence = Column(Float, nullable=True)
    probabilities = Column(Text, nullable=True)
    is_guest = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    emotion = Column(String(50))
    intensity = Column(Float)
    content_type = Column(String(50))
    content_confidence = Column(Float)
    duration_seconds = Column(Integer)
    is_guest = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())