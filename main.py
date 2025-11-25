from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import json
import logging
from datetime import datetime, timedelta, timezone
from database import engine, get_db, Base
from models import User, EmotionLog, AnalysisSession
from schemas import (
    UserSignup, UserLogin, UserResponse, 
    LoginResponse, SignupResponse, ReportData,
    ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, ResendVerificationRequest
)
from encryption import EncryptionService
from auth import create_access_token, get_current_user
from config import settings
from email_service import EmailService
from emotion_model import emotion_detector
from terms_and_conditions import TERMS_AND_CONDITIONS, PRIVACY_POLICY
from fastapi import Header

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NeuroLens API",
    description="Backend for NeuroLens Mental Well-being Monitor",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "NeuroLens API v1.0.0",
        "status": "running",
        "docs": "/docs",
        "guest_mode": "available"
    }


@app.post("/api/auth/signup", response_model=SignupResponse, status_code=201)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Create new user - Requires email verification"""
    
    email_normalized = user_data.email.lower().strip()
    username_normalized = user_data.username.lower().strip()
    
    print(f"📝 Signup attempt:")
    print(f"   Name: {user_data.name}")
    print(f"   Email: {email_normalized}")
    print(f"   Username: {username_normalized}")
    
    # Hash for lookup
    username_hash = EncryptionService.hash_username(username_normalized)
    email_hash = EncryptionService.hash_email(email_normalized)
    
    try:
        # Encrypt for storage/display
        encrypted_email = EncryptionService.encrypt_data(email_normalized)
        encrypted_username = EncryptionService.encrypt_data(username_normalized)
        print(f"✅ Data encrypted successfully")
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        raise HTTPException(status_code=500, detail="Encryption error")
    
    # Check existing user by hash (deterministic lookup)
    existing = db.query(User).filter(User.username_hash == username_hash).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    existing_email = db.query(User).filter(User.email_hash == email_hash).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    try:
        password_hash = EncryptionService.hash_password(user_data.password)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Password hashing error")
    
    # Generate verification code
    verification_code = EmailService.generate_verification_code()
    
    # Create user
    new_user = User(
        name=user_data.name.strip(),
        email_encrypted=encrypted_email,
        email_hash=email_hash,
        username_hash=username_hash,
        username_encrypted=encrypted_username,
        password_hash=password_hash,
        email_verified=False,
        verification_code=verification_code,
        verification_code_expiry=datetime.now(timezone.utc) + timedelta(minutes=10),
        is_active=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    print(f"✅ User created: ID={new_user.id}, Username={username_normalized}")
    print(f"📧 Verification code: {verification_code}")
    
    # Send verification email
    try:
        success = EmailService.send_verification_email(
            to_email=email_normalized,
            verification_code=verification_code,
            username=user_data.name
        )
        
        if success:
            print(f"✅ Verification email sent to {email_normalized}")
        else:
            print(f"⚠️ Failed to send verification email")
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
    
    # Generate temporary token (limited access until verified)
    token = create_access_token(data={"sub": username_normalized, "verified": False})
    
    return SignupResponse(
        token=token,
        user=UserResponse(
            id=new_user.id,
            name=new_user.name,
            email=email_normalized,
            username=username_normalized
        ),
        message="Account created! Please check your email for verification code."
    )


@app.post("/api/auth/verify-email")
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with code sent during signup"""
    
    email_normalized = request.email.lower().strip()
    code_normalized = request.code.strip()
    
    print(f"📧 Email verification attempt for: {email_normalized}")
    print(f"📝 Code provided: '{code_normalized}'")
    
    # Use email hash for lookup (deterministic)
    email_hash = EncryptionService.hash_email(email_normalized)
    
    # Find user by email hash
    user = db.query(User).filter(User.email_hash == email_hash).first()
    
    if not user:
        print(f"❌ User not found for email: {email_normalized}")
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    print(f"✅ User found: ID={user.id}, Name={user.name}")
    print(f"🔍 Stored code: '{user.verification_code}'")
    print(f"🔍 Code match: {user.verification_code == code_normalized}")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    if user.verification_code != code_normalized:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    if user.verification_code_expiry and user.verification_code_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")
    
    # Verify user
    user.email_verified = True
    user.is_active = True
    user.verification_code = None
    user.verification_code_expiry = None
    db.commit()
    
    print(f"✅ Email verified for {user.name}")
    
    try:
        EmailService.send_welcome_email(email_normalized, user.name)
    except Exception as e:
        print(f"⚠️ Welcome email failed: {e}")
    
    username = EncryptionService.decrypt_data(user.username_encrypted)
    token = create_access_token(data={"sub": username, "verified": True})
    
    return {
        "message": "Email verified successfully!",
        "token": token,
        "user": UserResponse(
            id=user.id,
            name=user.name,
            email=email_normalized,
            username=username
        )
    }


@app.post("/api/auth/resend-verification")
def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend verification code"""
    
    email_normalized = request.email.lower().strip()
    encrypted_email = EncryptionService.encrypt_data(email_normalized)
    
    user = db.query(User).filter(User.email_encrypted == encrypted_email).first()
    
    if not user:
        return {"message": "If this email exists, a new code has been sent"}
    
    if user.email_verified:
        return {"message": "Email already verified"}
    
    # Generate new code
    verification_code = EmailService.generate_verification_code()
    user.verification_code = verification_code
    user.verification_code_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()
    
    print(f"📧 Resending verification code to {email_normalized}")
    print(f"📝 New code: {verification_code}")
    
    # Send email
    try:
        EmailService.send_verification_email(
            to_email=email_normalized,
            verification_code=verification_code,
            username=user.name
        )
        print(f"✅ Verification email resent")
    except Exception as e:
        print(f"❌ Email sending error: {e}")
    
    return {"message": "If this email exists, a new code has been sent"}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user"""
    
    username_normalized = credentials.username.lower().strip()
    username_hash = EncryptionService.hash_username(username_normalized)
    
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not EncryptionService.verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if email is verified
    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox."
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    token = create_access_token(data={"sub": username_normalized, "verified": True})
    
    username_display = EncryptionService.decrypt_data(user.username_encrypted)
    email_display = EncryptionService.decrypt_data(user.email_encrypted)
    
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=email_display,
            username=username_display
        )
    )


@app.post("/api/auth/guest", response_model=LoginResponse)
def guest_login():
    """Guest mode - no signup required, limited features"""
    
    guest_id = f"guest_{datetime.now().timestamp()}"
    token = create_access_token(
        data={"sub": guest_id, "is_guest": True},
        expires_delta=timedelta(hours=24)
    )
    
    print(f"👤 Guest login: {guest_id}")
    
    return LoginResponse(
        token=token,
        user=UserResponse(
            id=0,
            name="Guest User",
            email="guest@neurolens.app",
            username=guest_id
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user"""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=EncryptionService.decrypt_data(current_user.email_encrypted),
        username=EncryptionService.decrypt_data(current_user.username_encrypted)
    )


@app.post("/api/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset code to email"""
    
    email_normalized = request.email.lower().strip()
    email_hash = EncryptionService.hash_email(email_normalized)
    
    user = db.query(User).filter(User.email_hash == email_hash).first()
    
    if not user:
        print(f"⚠️ Password reset requested for non-existent email: {email_normalized}")
        return {"message": "If this email is registered, a reset code has been sent"}
    
    reset_code = EmailService.generate_verification_code()
    
    user.reset_token = reset_code
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()
    
    print(f"🔐 Password reset code generated for {user.name}")
    print(f"📧 Reset code: {reset_code}")
    
    try:
        EmailService.send_password_reset_email(
            to_email=email_normalized,
            reset_code=reset_code,
            username=user.name
        )
        print(f"✅ Password reset email sent to {email_normalized}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
    
    return {
        "message": "If this email is registered, a reset code has been sent",
        "email": email_normalized
    }


@app.post("/api/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the emailed code"""
    
    email_normalized = request.email.lower().strip()
    email_hash = EncryptionService.hash_email(email_normalized)
    
    print(f"🔐 Password reset attempt for: {email_normalized}")
    print(f"📝 Code provided: {request.code}")
    
    user = db.query(User).filter(User.email_hash == email_hash).first()
    
    if not user:
        print(f"❌ Invalid email")
        raise HTTPException(
            status_code=400,
            detail="Invalid reset code or email"
        )
    
    if user.reset_token != request.code:
        print(f"❌ Invalid reset code")
        raise HTTPException(
            status_code=400,
            detail="Invalid reset code or email"
        )
    
    if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
        print(f"❌ Reset code expired")
        raise HTTPException(
            status_code=400,
            detail="Reset code expired. Please request a new one."
        )
    
    try:
        user.password_hash = EncryptionService.hash_password(request.new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.commit()
        
        print(f"✅ Password reset successful for {user.name}")
        
        return {
            "message": "Password reset successfully",
            "username": EncryptionService.decrypt_data(user.username_encrypted)
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Password reset failed: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed")


@app.post("/api/analyze/frame")
async def analyze_frame(
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze emotion from uploaded frame"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    username = getattr(current_user, 'username', 'guest')
    
    if not is_guest:
        username = EncryptionService.decrypt_data(current_user.username_encrypted)
    
    if emotion_detector and file:
        try:
            contents = await file.read()
            result = emotion_detector.analyze_frame(contents)
            
            emotions = ['happy', 'sad', 'angry', 'neutral', 'focused', 'stressed', 'tired']
            content_types = ['Studying', 'Coding', 'Video', 'Reading']
            
            emotion_data = {
                "emotion": result.get('emotion', 'neutral'),
                "intensity": result.get('intensity', 0.5),
                "content": random.choice(content_types),
                "content_conf": round(random.uniform(0.7, 1.0), 2),
                "timestamp": datetime.now().isoformat(),
                "face_detected": result.get('face_detected', False),
                "probabilities": result.get('probabilities', {})
            }
            
            try:
                emotion_log = EmotionLog(
                    user_id=current_user.id,
                    username=username,
                    emotion=emotion_data["emotion"],
                    intensity=emotion_data["intensity"],
                    content_type=emotion_data["content"],
                    content_confidence=emotion_data["content_conf"],
                    probabilities=json.dumps(emotion_data["probabilities"]),
                    is_guest=is_guest
                )
                db.add(emotion_log)
                
                # Update user's current emotion
                if not is_guest:
                    current_user.current_emotion = emotion_data["emotion"]
                    current_user.current_emotion_intensity = emotion_data["intensity"]
                    db.add(current_user)
                
                db.commit()
                print(f"✅ Emotion logged: {username} - {emotion_data['emotion']} ({emotion_data['intensity']:.2f})")
            except Exception as e:
                print(f"❌ Failed to save emotion log: {e}")
                db.rollback()
            
            return emotion_data
            
        except Exception as e:
            logger.error(f"Frame analysis error: {e}")
    
    # Fallback: random emotion data
    emotions = ['happy', 'neutral', 'focused', 'stressed', 'tired']
    content_types = ['Studying', 'Coding', 'Video', 'Reading']
    
    emotion_data = {
        "emotion": random.choice(emotions),
        "intensity": round(random.uniform(0.5, 1.0), 2),
        "content": random.choice(content_types),
        "content_conf": round(random.uniform(0.7, 1.0), 2),
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        emotion_log = EmotionLog(
            user_id=current_user.id,
            username=username,
            emotion=emotion_data["emotion"],
            intensity=emotion_data["intensity"],
            content_type=emotion_data["content"],
            content_confidence=emotion_data["content_conf"],
            probabilities="{}",
            is_guest=is_guest
        )
        db.add(emotion_log)
        
        # Update user's current emotion
        if not is_guest:
            current_user.current_emotion = emotion_data["emotion"]
            current_user.current_emotion_intensity = emotion_data["intensity"]
            db.add(current_user)
            
        db.commit()
    except Exception as e:
        print(f"❌ Failed to save emotion log: {e}")
        db.rollback()
    
    return emotion_data


@app.get("/api/emotions/history")
def get_emotion_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100
):
    """Get emotion detection history"""
    
    emotions = db.query(EmotionLog).filter(
        EmotionLog.user_id == current_user.id
    ).order_by(EmotionLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": e.id,
            "emotion": e.emotion,
            "intensity": e.intensity,
            "content_type": e.content_type,
            "timestamp": e.created_at.isoformat()
        }
        for e in emotions
    ]


@app.get("/api/terms")
def get_terms():
    """Get Terms and Conditions"""
    return {
        "terms": TERMS_AND_CONDITIONS,
        "last_updated": "2025-11-18"
    }


@app.get("/api/privacy")
def get_privacy():
    """Get Privacy Policy"""
    return {
        "privacy": PRIVACY_POLICY,
        "last_updated": "2025-11-18"
    }


# Admin authentication
ADMIN_API_KEY = "neurolens-admin-key-2025"  # Change in production!

def verify_admin(x_api_key: str = Header(None)):
    """Verify admin API key"""
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access denied")
    return True


@app.get("/api/admin/users")
def admin_get_users(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """Admin: Get all users"""
    
    users = db.query(User).offset(offset).limit(limit).all()
    
    return {
        "total": db.query(User).count(),
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": EncryptionService.decrypt_data(u.email_encrypted),
                "username": EncryptionService.decrypt_data(u.username_encrypted),
                "email_verified": u.email_verified,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat()
            }
            for u in users
        ]
    }


@app.get("/api/admin/emotion-logs")
def admin_get_emotion_logs(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
    limit: int = 1000,
    user_id: int = None
):
    """Admin: Get emotion logs for dataset management"""
    
    query = db.query(EmotionLog)
    
    if user_id:
        query = query.filter(EmotionLog.user_id == user_id)
    
    logs = query.order_by(EmotionLog.created_at.desc()).limit(limit).all()
    
    return {
        "total": query.count(),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "emotion": log.emotion,
                "intensity": log.intensity,
                "content_type": log.content_type,
                "timestamp": log.created_at.isoformat()
            }
            for log in logs
        ]
    }


@app.get("/api/admin/dataset/export")
def admin_export_dataset(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin: Export emotion dataset for model training"""
    
    logs = db.query(EmotionLog).all()
    
    return {
        "dataset": [
            {
                "emotion": log.emotion,
                "intensity": log.intensity,
                "content_type": log.content_type,
                "probabilities": log.probabilities,
                "timestamp": log.created_at.isoformat()
            }
            for log in logs
        ],
        "total_samples": len(logs),
        "emotion_distribution": {
            emotion: db.query(EmotionLog).filter(EmotionLog.emotion == emotion).count()
            for emotion in ['happy', 'sad', 'angry', 'neutral', 'focused', 'stressed', 'tired']
        }
    }


@app.get("/api/admin/audit")
def admin_get_audit(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin: Get system audit log"""
    
    # Get system statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.email_verified == True).count()
    total_sessions = db.query(EmotionLog).count()
    
    # Get recent activity
    recent_signups = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    recent_sessions = db.query(EmotionLog).order_by(EmotionLog.created_at.desc()).limit(20).all()
    
    return {
        "statistics": {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "total_emotion_logs": total_sessions,
            "guest_sessions": db.query(EmotionLog).filter(EmotionLog.is_guest == True).count()
        },
        "recent_activity": {
            "signups": [
                {
                    "id": u.id,
                    "name": u.name,
                    "created_at": u.created_at.isoformat()
                }
                for u in recent_signups
            ],
            "sessions": [
                {
                    "username": s.username,
                    "emotion": s.emotion,
                    "timestamp": s.created_at.isoformat()
                }
                for s in recent_sessions
            ]
        }
    }


@app.get("/api/admin/stats")
def admin_get_stats(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin: Get comprehensive statistics"""
    
    from sqlalchemy import func
    
    # Emotion distribution
    emotion_dist = db.query(
        EmotionLog.emotion,
        func.count(EmotionLog.id).label('count')
    ).group_by(EmotionLog.emotion).all()
    
    # Daily activity (last 7 days)
    from datetime import date, timedelta
    today = date.today()
    daily_activity = []
    
    for i in range(7):
        day = today - timedelta(days=i)
        count = db.query(EmotionLog).filter(
            func.date(EmotionLog.created_at) == day
        ).count()
        daily_activity.append({
            "date": day.isoformat(),
            "sessions": count
        })
    
    return {
        "emotion_distribution": {e: c for e, c in emotion_dist},
        "daily_activity": daily_activity,
        "top_users": [
            {
                "username": log.username,
                "session_count": db.query(EmotionLog).filter(
                    EmotionLog.username == log.username
                ).count()
            }
            for log in db.query(EmotionLog.username).distinct().limit(10).all()
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)