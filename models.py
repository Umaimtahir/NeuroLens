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
    
    # Login attempt tracking (lockout after 5 failed attempts)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # ✅ Current state tracking (ADD THESE)
    current_emotion = Column(String(50), nullable=True)
    current_emotion_intensity = Column(Float, nullable=True)
    current_content = Column(String(50), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    is_recording = Column(Boolean, default=False, nullable=False)  # Track active recording state
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


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


class ContentSession(Base):
    """Track content consumption sessions with duration and activity type"""
    __tablename__ = "content_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=False)
    
    # Content classification
    content_type = Column(String(50), nullable=False, index=True)   # e.g. VIDEO/STREAMING, CODING/DEVELOPMENT
    content_confidence = Column(Float, nullable=True)
    
    # Activity classification (what the user is DOING)
    activity = Column(String(50), nullable=False, index=True)       # e.g. WATCHING, CODING, READING, WRITING
    activity_emoji = Column(String(10), nullable=True)
    activity_confidence = Column(String(20), nullable=True)
    
    # Productivity classification
    productivity = Column(String(20), nullable=True)                 # PRODUCTIVE, NEUTRAL, UNPRODUCTIVE
    productivity_emoji = Column(String(10), nullable=True)
    
    # Window/app details
    app_name = Column(String(100), nullable=True)
    window_title = Column(String(500), nullable=True)
    
    # Time tracking
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)               # computed when session ends
    
    is_active = Column(Boolean, default=True)                       # is this session still ongoing?
    is_guest = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Store all system audit events for admin review"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)  # Null for system events
    username = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., 'LOGIN', 'LOGOUT', 'SIGNUP', etc.
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(20), default='success')  # 'success', 'failed', 'pending'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)