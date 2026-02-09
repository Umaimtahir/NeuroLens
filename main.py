from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import json
import logging
from datetime import datetime, timedelta, timezone
from database import engine, get_db, Base
from models import User, EmotionLog, AnalysisSession, AuditLog, ContentSession
from schemas import (
    UserSignup, UserLogin, UserResponse, 
    LoginResponse, SignupResponse, ReportData,
    ForgotPasswordRequest, ResetPasswordRequest, VerifyResetCodeRequest,
    VerifyEmailRequest, ResendVerificationRequest,
    InitiateSignupResponse, VerifySignupRequest,
    UpdateProfileRequest, VerifyProfileUpdateRequest, ChangePasswordRequest
)
from encryption import EncryptionService
from auth import create_access_token, get_current_user
from config import settings
from email_service import EmailService
from emotion_model import emotion_detector
from terms_and_conditions import TERMS_AND_CONDITIONS, PRIVACY_POLICY
from fastapi import Header

# Content Classification - Use lightweight Windows API detection (fast, no ML)
content_analyzer = None
CONTENT_CLASSIFIER_AVAILABLE = False
windows_api = None
activity_classifier = None

# In-memory session tracker: {user_id: {"content_type": ..., "activity": ..., "started_at": ..., "session_id": ...}}
active_content_sessions = {}

def get_fast_content_detector():
    """Get fast Windows API-based content detector (no ML models)"""
    global windows_api
    if windows_api is None:
        try:
            from window_detector import WindowsAPI
            windows_api = WindowsAPI()
            print("✅ Fast content detector (Windows API) loaded!")
        except Exception as e:
            print(f"⚠️ Fast content detector not available: {e}")
    return windows_api

def get_activity_classifier():
    """Get the activity classifier (lightweight, no ML models)"""
    global activity_classifier
    if activity_classifier is None:
        try:
            from window_detector import ActivityClassifier
            activity_classifier = ActivityClassifier()
            print("✅ Activity classifier loaded!")
        except Exception as e:
            print(f"⚠️ Activity classifier not available: {e}")
    return activity_classifier


def _classify_activity(app_name: str, window_title: str, category: str) -> dict:
    """Classify user activity (WATCHING, READING, CODING, etc.) from window info."""
    classifier = get_activity_classifier()
    if classifier:
        try:
            return classifier.classify(
                app_name=app_name,
                window_title=window_title,
                category=category,
            )
        except Exception as e:
            print(f"⚠️ Activity classification error: {e}")
    return {
        'activity': 'BROWSING',
        'emoji': '🌐',
        'confidence': 'Low',
        'score': 0,
        'reason': 'classifier unavailable'
    }


def _get_productivity(activity: str, category: str) -> dict:
    """Simple rule-based productivity classification (no ML overhead)."""
    activity_upper = (activity or '').upper()
    category_upper = (category or '').upper()

    productive_activities = ['CODING', 'LEARNING', 'WRITING', 'READING', 'DESIGNING']
    unproductive_activities = ['GAMING', 'WATCHING', 'SHOPPING']

    productive_categories = ['CODING/DEVELOPMENT', 'EDUCATION', 'DOCUMENT/PRODUCTIVITY', 'DATABASE', 'DEVOPS', 'API TESTING']
    unproductive_categories = ['GAMING', 'VIDEO/STREAMING', 'SOCIAL MEDIA']

    if activity_upper in productive_activities or category_upper in productive_categories:
        return {'classification': 'PRODUCTIVE', 'emoji': '✅'}
    elif activity_upper in unproductive_activities or category_upper in unproductive_categories:
        return {'classification': 'UNPRODUCTIVE', 'emoji': '⚠️'}
    return {'classification': 'NEUTRAL', 'emoji': '➖'}


def _update_content_session(db: Session, user_id: int, username: str,
                            content_type: str, content_confidence: float,
                            activity: str, activity_emoji: str, activity_confidence: str,
                            productivity: str, productivity_emoji: str,
                            app_name: str, window_title: str, is_guest: bool):
    """
    Track content sessions with time duration.
    If the user is still on the same content_type+activity, keep the session.
    If content/activity changed, close the old session and open a new one.
    """
    now = datetime.now(timezone.utc)
    session_key = user_id

    prev = active_content_sessions.get(session_key)

    # Check if same session continues (same content + activity)
    same_session = (
        prev is not None
        and prev.get('content_type') == content_type
        and prev.get('activity') == activity
    )

    if same_session:
        # Session continues – update duration in DB periodically (every call)
        try:
            session_row = db.query(ContentSession).filter(
                ContentSession.id == prev['session_id'],
                ContentSession.is_active == True
            ).first()
            if session_row:
                session_row.duration_seconds = int((now - prev['started_at']).total_seconds())
                session_row.ended_at = now
                db.flush()
        except Exception as e:
            print(f"⚠️ Session update error: {e}")
        return prev.get('session_id')

    # --- Content/activity changed OR first call ---

    # Close previous session
    if prev and prev.get('session_id'):
        try:
            old_session = db.query(ContentSession).filter(
                ContentSession.id == prev['session_id'],
                ContentSession.is_active == True
            ).first()
            if old_session:
                old_session.is_active = False
                old_session.ended_at = now
                old_session.duration_seconds = int((now - prev['started_at']).total_seconds())
                db.flush()
                print(f"⏱️ Session ended: {prev['content_type']}/{prev['activity']} — {old_session.duration_seconds}s")
        except Exception as e:
            print(f"⚠️ Close old session error: {e}")

    # Open new session
    try:
        new_session = ContentSession(
            user_id=user_id,
            username=username,
            content_type=content_type or 'UNKNOWN',
            content_confidence=content_confidence,
            activity=activity or 'BROWSING',
            activity_emoji=activity_emoji,
            activity_confidence=activity_confidence,
            productivity=productivity,
            productivity_emoji=productivity_emoji,
            app_name=(app_name or '')[:100],
            window_title=(window_title or '')[:500],
            started_at=now,
            is_active=True,
            is_guest=is_guest
        )
        db.add(new_session)
        db.flush()  # get new_session.id

        active_content_sessions[session_key] = {
            'session_id': new_session.id,
            'content_type': content_type,
            'activity': activity,
            'started_at': now,
        }
        print(f"▶️ New session: {content_type}/{activity} (id={new_session.id})")
        return new_session.id
    except Exception as e:
        print(f"⚠️ New session error: {e}")
        return None

def get_content_analyzer():
    """Lazy load the full content analyzer (heavy ML models) - use sparingly"""
    global content_analyzer, CONTENT_CLASSIFIER_AVAILABLE
    if content_analyzer is None and not CONTENT_CLASSIFIER_AVAILABLE:
        try:
            from screen_classifer import HybridAnalyzer
            print("🔄 Loading Full Content Classifier (ML models)...")
            content_analyzer = HybridAnalyzer(enable_ocr=False)
            CONTENT_CLASSIFIER_AVAILABLE = True
            print("✅ Full Content Classifier loaded!")
        except Exception as e:
            print(f"⚠️ Full Content Classifier not available: {e}")
            CONTENT_CLASSIFIER_AVAILABLE = False
    return content_analyzer

logger = logging.getLogger(__name__)

# Temporary storage for pending signups (email verification before account creation)
# Format: {email_hash: {"data": {...}, "code": "123456", "expiry": datetime}}
pending_signups = {}

# Temporary storage for pending profile updates (email verification before update)
# Format: {user_id: {"updates": {...}, "new_email": "...", "code": "123456", "expiry": datetime}}
pending_profile_updates = {}

# Create tables
Base.metadata.create_all(bind=engine)


def log_audit_event(
    db: Session,
    action: str,
    user_id: int = None,
    username: str = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None,
    status: str = "success"
):
    """Helper function to log audit events"""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )
        db.add(audit_entry)
        db.commit()
        print(f"📝 Audit: {action} - {username or 'System'} - {status}")
    except Exception as e:
        print(f"⚠️ Audit log error: {e}")


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


@app.post("/api/auth/signup", response_model=InitiateSignupResponse, status_code=200)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """Initiate signup - Sends verification code to email BEFORE creating account"""
    
    email_normalized = user_data.email.lower().strip()
    username_normalized = user_data.username.lower().strip()
    
    print(f"📝 Signup initiation attempt:")
    print(f"   Name: {user_data.name}")
    print(f"   Email: {email_normalized}")
    print(f"   Username: {username_normalized}")
    
    # Hash for lookup
    username_hash = EncryptionService.hash_username(username_normalized)
    email_hash = EncryptionService.hash_email(email_normalized)
    
    # Check existing user by hash (deterministic lookup)
    existing = db.query(User).filter(User.username_hash == username_hash).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    existing_email = db.query(User).filter(User.email_hash == email_hash).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate verification code
    verification_code = EmailService.generate_verification_code()
    
    # Store pending signup data (will create account after email verification)
    pending_signups[email_hash] = {
        "data": {
            "name": user_data.name.strip(),
            "email": email_normalized,
            "username": username_normalized,
            "password": user_data.password  # Will be hashed when account is created
        },
        "code": verification_code,
        "expiry": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    
    print(f"📧 Verification code: {verification_code}")
    print(f"⏳ Pending signup stored for: {email_normalized}")
    
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
            print(f"⚠️ Failed to send verification email (check email settings)")
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
    
    return InitiateSignupResponse(
        message="Verification code sent to your email. Please verify to complete signup.",
        email=email_normalized
    )


@app.post("/api/auth/verify-signup", response_model=SignupResponse, status_code=201)
def verify_signup(request: VerifySignupRequest, db: Session = Depends(get_db)):
    """Verify email code and create account"""
    
    email_normalized = request.email.lower().strip()
    code_normalized = request.code.strip()
    
    print(f"📧 Signup verification attempt for: {email_normalized}")
    print(f"📝 Code provided: '{code_normalized}'")
    
    # Get email hash for lookup
    email_hash = EncryptionService.hash_email(email_normalized)
    
    # Check if there's a pending signup for this email
    pending = pending_signups.get(email_hash)
    
    if not pending:
        print(f"❌ No pending signup found for: {email_normalized}")
        raise HTTPException(status_code=400, detail="No pending signup found. Please start signup again.")
    
    # Check if code has expired
    if pending["expiry"] < datetime.now(timezone.utc):
        # Clean up expired entry
        del pending_signups[email_hash]
        print(f"❌ Verification code expired for: {email_normalized}")
        raise HTTPException(status_code=400, detail="Verification code expired. Please start signup again.")
    
    # Verify code
    if pending["code"] != code_normalized:
        print(f"❌ Invalid code: expected '{pending['code']}', got '{code_normalized}'")
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Code is valid - now create the account
    signup_data = pending["data"]
    
    try:
        # Encrypt for storage
        encrypted_email = EncryptionService.encrypt_data(signup_data["email"])
        encrypted_username = EncryptionService.encrypt_data(signup_data["username"])
        password_hash = EncryptionService.hash_password(signup_data["password"])
        username_hash = EncryptionService.hash_username(signup_data["username"])
        print(f"✅ Data encrypted successfully")
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        raise HTTPException(status_code=500, detail="Encryption error")
    
    # Create user (already verified)
    new_user = User(
        name=signup_data["name"],
        email_encrypted=encrypted_email,
        email_hash=email_hash,
        username_hash=username_hash,
        username_encrypted=encrypted_username,
        password_hash=password_hash,
        email_verified=True,  # Already verified!
        verification_code=None,
        verification_code_expiry=None,
        is_active=True  # Account is active immediately
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Clean up pending signup
    del pending_signups[email_hash]
    
    print(f"✅ User created and verified: ID={new_user.id}, Username={signup_data['username']}")
    
    # Log signup audit event
    log_audit_event(db, "SIGNUP_SUCCESS", user_id=new_user.id, username=signup_data["username"],
                   details=json.dumps({"email": signup_data["email"], "name": signup_data["name"]}))
    
    # Send welcome email
    try:
        EmailService.send_welcome_email(signup_data["email"], signup_data["name"])
    except Exception as e:
        print(f"⚠️ Welcome email failed: {e}")
    
    # Generate token (fully verified) - include user_id for auth after username changes
    token = create_access_token(data={"sub": signup_data["username"], "user_id": new_user.id, "verified": True})
    
    return SignupResponse(
        token=token,
        user=UserResponse(
            id=new_user.id,
            name=new_user.name,
            email=signup_data["email"],
            username=signup_data["username"]
        ),
        message="Account created and verified successfully!"
    )


@app.post("/api/auth/resend-signup-code")
def resend_signup_code(email: str, db: Session = Depends(get_db)):
    """Resend verification code for pending signup"""
    
    email_normalized = email.lower().strip()
    email_hash = EncryptionService.hash_email(email_normalized)
    
    pending = pending_signups.get(email_hash)
    
    if not pending:
        raise HTTPException(status_code=400, detail="No pending signup found. Please start signup again.")
    
    # Generate new code
    new_code = EmailService.generate_verification_code()
    pending["code"] = new_code
    pending["expiry"] = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    print(f"📧 New verification code: {new_code}")
    
    # Send email
    try:
        EmailService.send_verification_email(
            to_email=email_normalized,
            verification_code=new_code,
            username=pending["data"]["name"]
        )
    except Exception as e:
        print(f"❌ Email sending error: {e}")
    
    return {"message": "Verification code resent to your email"}


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
    token = create_access_token(data={"sub": username, "user_id": user.id, "verified": True})
    
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
def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Authenticate user"""
    
    username_normalized = credentials.username.lower().strip()
    username_hash = EncryptionService.hash_username(username_normalized)
    
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if not user:
        print(f"❌ LOGIN FAILED: User '{username_normalized}' not found")
        log_audit_event(db, "LOGIN_FAILED", username=username_normalized, 
                       details="User not found", status="failed",
                       ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
        remaining_time = (user.account_locked_until - datetime.now(timezone.utc)).total_seconds()
        remaining_mins = int(remaining_time / 60)
        print(f"🔒 LOGIN BLOCKED: Account '{username_normalized}' is locked ({remaining_mins} mins remaining)")
        log_audit_event(db, "LOGIN_BLOCKED", user_id=user.id, username=username_normalized,
                       details=f"Account locked, {int(remaining_time)}s remaining", status="failed",
                       ip_address=request.client.host if request.client else None)
        raise HTTPException(
            status_code=423,  # Locked status code
            detail=json.dumps({
                "message": "Account locked due to too many failed attempts",
                "locked": True,
                "remaining_seconds": int(remaining_time),
                "failed_attempts": user.failed_login_attempts
            })
        )
    
    if not EncryptionService.verify_password(credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        print(f"❌ LOGIN FAILED: Invalid password for '{username_normalized}' (attempt {user.failed_login_attempts}/5)")
        
        # Lock account after 5 failed attempts (lock for 30 minutes)
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            db.commit()
            print(f"🔒 ACCOUNT LOCKED: '{username_normalized}' locked for 30 minutes after {user.failed_login_attempts} failed attempts")
            log_audit_event(db, "ACCOUNT_LOCKED", user_id=user.id, username=username_normalized,
                           details=f"Account locked after {user.failed_login_attempts} failed attempts", status="failed",
                           ip_address=request.client.host if request.client else None)
            raise HTTPException(
                status_code=423,
                detail=json.dumps({
                    "message": "Account locked due to too many failed attempts. Please reset your password.",
                    "locked": True,
                    "remaining_seconds": 1800,  # 30 minutes
                    "failed_attempts": user.failed_login_attempts
                })
            )
        
        db.commit()
        log_audit_event(db, "LOGIN_FAILED", user_id=user.id, username=username_normalized,
                       details=f"Invalid password (attempt {user.failed_login_attempts}/5)", status="failed",
                       ip_address=request.client.host if request.client else None)
        raise HTTPException(
            status_code=401, 
            detail=json.dumps({
                "message": "Invalid credentials",
                "failed_attempts": user.failed_login_attempts,
                "remaining_attempts": 5 - user.failed_login_attempts
            })
        )
    
    # Check if email is verified
    if not user.email_verified:
        log_audit_event(db, "LOGIN_FAILED", user_id=user.id, username=username_normalized,
                       details="Email not verified", status="failed",
                       ip_address=request.client.host if request.client else None)
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox."
        )
    
    if not user.is_active:
        log_audit_event(db, "LOGIN_FAILED", user_id=user.id, username=username_normalized,
                       details="Account disabled", status="failed",
                       ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=403, detail="Account disabled")
    
    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.account_locked_until = None
    db.commit()
    
    token = create_access_token(data={"sub": username_normalized, "user_id": user.id, "verified": True})
    
    username_display = EncryptionService.decrypt_data(user.username_encrypted)
    email_display = EncryptionService.decrypt_data(user.email_encrypted)
    
    # Log successful login
    print(f"✅ LOGIN SUCCESS: User '{username_display}' logged in successfully")
    log_audit_event(db, "LOGIN_SUCCESS", user_id=user.id, username=username_display,
                   details=json.dumps({"email": email_display}),
                   ip_address=request.client.host if request.client else None)
    
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
    # Handle guest users
    if current_user.id == 0 or not current_user.email_encrypted:
        return UserResponse(
            id=0,
            name="Guest User",
            email="guest@neurolens.app",
            username="guest"
        )
    
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=EncryptionService.decrypt_data(current_user.email_encrypted),
        username=EncryptionService.decrypt_data(current_user.username_encrypted)
    )


@app.post("/api/auth/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset code to email - validates username and email match"""
    
    email_normalized = request.email.lower().strip()
    username_normalized = request.username.lower().strip()
    
    email_hash = EncryptionService.hash_email(email_normalized)
    username_hash = EncryptionService.hash_username(username_normalized)
    
    # Find user by username
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if not user:
        print(f"⚠️ Password reset requested for non-existent username: {username_normalized}")
        raise HTTPException(
            status_code=404,
            detail="Username not found"
        )
    
    # Verify email matches
    if user.email_hash != email_hash:
        print(f"⚠️ Email mismatch for username: {username_normalized}")
        raise HTTPException(
            status_code=400,
            detail="Email does not match the registered email for this username"
        )
    
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
        "message": "Reset code sent to your email",
        "email": email_normalized,
        "username": username_normalized
    }


@app.post("/api/auth/verify-reset-code")
def verify_reset_code(request: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    """Verify the reset code before allowing password reset"""
    
    email_normalized = request.email.lower().strip()
    username_normalized = request.username.lower().strip()
    
    email_hash = EncryptionService.hash_email(email_normalized)
    username_hash = EncryptionService.hash_username(username_normalized)
    
    # Find user by username
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Verify email matches
    if user.email_hash != email_hash:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Verify reset code
    if user.reset_token != request.code:
        raise HTTPException(status_code=400, detail="Invalid reset code")
    
    # Check if code expired
    if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset code has expired. Please request a new one.")
    
    print(f"✅ Reset code verified for {user.name}")
    
    return {
        "message": "Code verified successfully",
        "verified": True
    }


@app.post("/api/auth/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using the emailed code"""
    
    email_normalized = request.email.lower().strip()
    username_normalized = request.username.lower().strip()
    
    email_hash = EncryptionService.hash_email(email_normalized)
    username_hash = EncryptionService.hash_username(username_normalized)
    
    print(f"🔐 Password reset attempt for: {username_normalized} / {email_normalized}")
    print(f"📝 Code provided: {request.code}")
    
    # Find user by username
    user = db.query(User).filter(User.username_hash == username_hash).first()
    
    if not user:
        print(f"❌ Invalid username")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    # Verify email matches
    if user.email_hash != email_hash:
        print(f"❌ Email mismatch")
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    if user.reset_token != request.code:
        print(f"❌ Invalid reset code")
        raise HTTPException(status_code=400, detail="Invalid reset code")
    
    if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
        print(f"❌ Reset code expired")
        raise HTTPException(status_code=400, detail="Reset code expired. Please request a new one.")
    
    try:
        user.password_hash = EncryptionService.hash_password(request.new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        # Reset failed login attempts and unlock account
        user.failed_login_attempts = 0
        user.account_locked_until = None
        db.commit()
        
        username_display = EncryptionService.decrypt_data(user.username_encrypted)
        print(f"✅ Password reset successful for {user.name}")
        
        # Log password reset audit event
        log_audit_event(db, "PASSWORD_RESET", user_id=user.id, username=username_display,
                       details=json.dumps({"email": email_normalized}))
        
        return {
            "message": "Password reset successfully",
            "username": username_display
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Password reset failed: {e}")
        log_audit_event(db, "PASSWORD_RESET_FAILED", username=username_normalized,
                       details=str(e), status="failed")
        raise HTTPException(status_code=500, detail="Password reset failed")


# ==================== PROFILE UPDATE ENDPOINTS ====================

@app.get("/api/profile")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    if is_guest or current_user.id == 0:
        return {
            "id": 0,
            "name": "Guest User",
            "email": "guest@neurolens.app",
            "username": "guest",
            "is_guest": True
        }
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    username_display = EncryptionService.decrypt_data(user.username_encrypted)
    email_display = EncryptionService.decrypt_data(user.email_encrypted)
    
    return {
        "id": user.id,
        "name": user.name,
        "email": email_display,
        "username": username_display,
        "is_guest": False
    }


@app.put("/api/profile")
def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile (name, email, username).
    If email is changed, sends verification code to new email.
    """
    
    is_guest = getattr(current_user, 'is_guest', False)
    if is_guest or current_user.id == 0:
        raise HTTPException(status_code=403, detail="Guests cannot update profile")
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_username = EncryptionService.decrypt_data(user.username_encrypted)
    current_email = EncryptionService.decrypt_data(user.email_encrypted)
    
    updates_applied = []
    email_change_pending = False
    new_email = None
    
    # Check and update name
    if request.name and request.name != user.name:
        user.name = request.name
        updates_applied.append("name")
        print(f"📝 Updating name to: {request.name}")
    
    # Check and update username
    if request.username and request.username.lower() != current_username.lower():
        new_username = request.username.lower().strip()
        new_username_hash = EncryptionService.hash_username(new_username)
        
        # Check if username already exists
        existing_user = db.query(User).filter(
            User.username_hash == new_username_hash,
            User.id != user.id
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Update username
        user.username_hash = new_username_hash
        user.username_encrypted = EncryptionService.encrypt_data(new_username)
        updates_applied.append("username")
        print(f"📝 Updating username to: {new_username}")
    
    # Check and update email (requires verification)
    if request.email and request.email.lower() != current_email.lower():
        new_email = request.email.lower().strip()
        new_email_hash = EncryptionService.hash_email(new_email)
        
        # Check if email already exists
        existing_user = db.query(User).filter(
            User.email_hash == new_email_hash,
            User.id != user.id
        ).first()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate verification code
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store pending update
        pending_profile_updates[user.id] = {
            "new_email": new_email,
            "new_email_hash": new_email_hash,
            "new_email_encrypted": EncryptionService.encrypt_data(new_email),
            "code": verification_code,
            "expiry": datetime.now(timezone.utc) + timedelta(minutes=15)
        }
        
        # Print verification code to terminal for debugging
        print(f"📧 Profile Email Change Verification Code: {verification_code}")
        print(f"   New email: {new_email}")
        
        # Send verification email
        try:
            EmailService.send_verification_email(
                to_email=new_email,
                verification_code=verification_code,
                username=user.name
            )
            print(f"✅ Verification email sent to: {new_email}")
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
        
        email_change_pending = True
    
    # Commit name/username changes
    if updates_applied:
        db.commit()
        log_audit_event(db, "PROFILE_UPDATED", user_id=user.id, username=current_username,
                       details=json.dumps({"updated_fields": updates_applied}))
    
    # Get updated display values
    updated_username = EncryptionService.decrypt_data(user.username_encrypted)
    updated_email = EncryptionService.decrypt_data(user.email_encrypted)
    
    # Generate new token if username changed (so auth continues to work)
    new_token = None
    if "username" in updates_applied:
        new_token = create_access_token(data={"sub": updated_username, "user_id": user.id, "verified": True})
    
    response = {
        "message": "Profile updated successfully" if updates_applied else "No changes made",
        "email_verification_required": email_change_pending,
        "updates_applied": updates_applied,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": updated_email,
            "username": updated_username
        }
    }
    
    if new_token:
        response["new_token"] = new_token
    
    return response


@app.post("/api/profile/verify-email")
def verify_profile_email_update(
    request: VerifyProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify email change with code"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    if is_guest or current_user.id == 0:
        raise HTTPException(status_code=403, detail="Guests cannot update profile")
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for pending update
    pending = pending_profile_updates.get(user.id)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending email change found")
    
    # Check expiry
    if pending["expiry"] < datetime.now(timezone.utc):
        del pending_profile_updates[user.id]
        raise HTTPException(status_code=400, detail="Verification code expired")
    
    # Verify code
    if pending["code"] != request.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    current_username = EncryptionService.decrypt_data(user.username_encrypted)
    old_email = EncryptionService.decrypt_data(user.email_encrypted)
    
    # Apply email update
    user.email_hash = pending["new_email_hash"]
    user.email_encrypted = pending["new_email_encrypted"]
    db.commit()
    
    # Clean up
    del pending_profile_updates[user.id]
    
    log_audit_event(db, "EMAIL_CHANGED", user_id=user.id, username=current_username,
                   details=json.dumps({"old_email": old_email, "new_email": pending["new_email"]}))
    
    return {
        "message": "Email updated successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": pending["new_email"],
            "username": current_username
        }
    }


@app.post("/api/profile/resend-verification")
def resend_profile_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resend verification code for pending email change"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    if is_guest or current_user.id == 0:
        raise HTTPException(status_code=403, detail="Guests cannot update profile")
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    pending = pending_profile_updates.get(user.id)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending email change found")
    
    # Generate new code
    verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    pending["code"] = verification_code
    pending["expiry"] = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Print new verification code to terminal
    print(f"📧 Profile Email Change Verification Code (Resent): {verification_code}")
    print(f"   Email: {pending['new_email']}")
    
    try:
        EmailService.send_verification_email(
            to_email=pending["new_email"],
            verification_code=verification_code,
            username=user.name
        )
        print(f"✅ Verification email resent to: {pending['new_email']}")
        return {"message": "Verification code resent"}
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email")


@app.post("/api/profile/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (requires current password)"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    if is_guest or current_user.id == 0:
        raise HTTPException(status_code=403, detail="Guests cannot change password")
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_username = EncryptionService.decrypt_data(user.username_encrypted)
    
    # Verify current password
    if not EncryptionService.verify_password(request.current_password, user.password_hash):
        log_audit_event(db, "PASSWORD_CHANGE_FAILED", user_id=user.id, username=current_username,
                       details="Invalid current password", status="failed")
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Update password
    user.password_hash = EncryptionService.hash_password(request.new_password)
    db.commit()
    
    log_audit_event(db, "PASSWORD_CHANGED", user_id=user.id, username=current_username,
                   details="Password changed successfully")
    
    return {"message": "Password changed successfully"}


# ==================== RECORDING STATE MANAGEMENT ====================

@app.post("/api/recording/start")
def start_recording(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark recording as started for current user"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    
    if is_guest or current_user.id == 0:
        return {"status": "recording", "message": "Guest recording started"}
    
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        if user:
            user.is_recording = True
            user.last_activity = datetime.now(timezone.utc)
            db.commit()
            print(f"🎬 Recording started for user: {current_user.id}")
        
        return {"status": "recording", "message": "Recording started"}
    except Exception as e:
        print(f"❌ Failed to start recording: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to start recording")


@app.post("/api/recording/stop")
def stop_recording(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark recording as stopped for current user and close any active content session"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    
    if is_guest or current_user.id == 0:
        # Clear in-memory session for guest
        active_content_sessions.pop(current_user.id, None)
        return {"status": "idle", "message": "Guest recording stopped"}
    
    try:
        now = datetime.now(timezone.utc)
        user = db.query(User).filter(User.id == current_user.id).first()
        if user:
            user.is_recording = False
        
        # Close active content session in DB
        active_sessions = db.query(ContentSession).filter(
            ContentSession.user_id == current_user.id,
            ContentSession.is_active == True
        ).all()
        for sess in active_sessions:
            sess.is_active = False
            sess.ended_at = now
            if sess.started_at:
                sess.duration_seconds = int((now - sess.started_at).total_seconds())
        
        # Clear in-memory tracker
        active_content_sessions.pop(current_user.id, None)
        
        db.commit()
        print(f"⏹️ Recording stopped for user: {current_user.id} ({len(active_sessions)} session(s) closed)")
        
        return {"status": "idle", "message": "Recording stopped"}
    except Exception as e:
        print(f"❌ Failed to stop recording: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to stop recording")


@app.post("/api/analyze/frame")
async def analyze_frame(
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze emotion from uploaded frame with content + activity classification + time tracking"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    username = getattr(current_user, 'username', 'guest')
    
    if not is_guest:
        username = EncryptionService.decrypt_data(current_user.username_encrypted)
    
    # ===== CONTENT CLASSIFICATION (Windows API - fast, no ML) =====
    content_type = None
    content_confidence = None
    app_name = ""
    window_title = ""
    
    fast_detector = get_fast_content_detector()
    if fast_detector:
        try:
            content_result = fast_detector.categorize_from_window()
            content_type = content_result.get('category', 'OTHER')
            app_name = content_result.get('app', '')
            window_title = content_result.get('title', '')
            confidence_map = {'Very High': 0.95, 'High': 0.80, 'Medium': 0.60, 'Low': 0.40}
            content_confidence = confidence_map.get(content_result.get('confidence', 'Low'), 0.40)
        except Exception as e:
            print(f"⚠️ Content detection failed: {e}")
    
    # ===== ACTIVITY CLASSIFICATION (WATCHING, READING, CODING, etc.) =====
    activity_result = _classify_activity(app_name, window_title, content_type or "")
    activity = activity_result.get('activity', 'BROWSING')
    activity_emoji = activity_result.get('emoji', '🌐')
    activity_confidence = activity_result.get('confidence', 'Low')
    
    # ===== PRODUCTIVITY CLASSIFICATION =====
    productivity_result = _get_productivity(activity, content_type)
    productivity = productivity_result['classification']
    productivity_emoji = productivity_result['emoji']
    
    # Build content details dict for API response
    content_details = {
        'app_name': app_name,
        'window_title': window_title[:200],
        'activity': activity,
        'activity_emoji': activity_emoji,
        'activity_confidence': activity_confidence,
        'productivity': productivity,
        'productivity_emoji': productivity_emoji,
    }
    
    print(f"📊 Content: {content_type} | Activity: {activity_emoji} {activity} | Productivity: {productivity_emoji} {productivity}")
    
    # ===== CONTENT SESSION TIME TRACKING =====
    session_id = None
    try:
        session_id = _update_content_session(
            db=db,
            user_id=current_user.id,
            username=username,
            content_type=content_type or "UNKNOWN",
            content_confidence=content_confidence,
            activity=activity,
            activity_emoji=activity_emoji,
            activity_confidence=activity_confidence,
            productivity=productivity,
            productivity_emoji=productivity_emoji,
            app_name=app_name,
            window_title=window_title,
            is_guest=is_guest
        )
    except Exception as e:
        print(f"⚠️ Session tracking error: {e}")
    
    # ===== EMOTION DETECTION =====
    if file:
        try:
            contents = await file.read()
            print(f"📷 Received frame: {len(contents)} bytes from {username}")
            result = emotion_detector.process_frame(contents) if emotion_detector else None
            
            if result:
                print(f"🧠 Model result: {result.get('emotion')} ({result.get('intensity', 0):.2f}) - Face detected: {result.get('face_detected', False)}")
                emotion_data = {
                    "emotion": result.get('emotion', 'neutral'),
                    "intensity": result.get('intensity', 0.5),
                    "content": content_type or "UNKNOWN",
                    "content_conf": content_confidence or 0.0,
                    "content_details": content_details,
                    "timestamp": datetime.now().isoformat(),
                    "face_detected": result.get('face_detected', False),
                    "probabilities": result.get('probabilities', {}),
                    "error": result.get('error'),
                    "error_message": result.get('error_message'),
                    "stop_detection": result.get('stop_detection', False),
                    "face_count": result.get('face_count', 1)
                }
            else:
                emotion_data = {
                    "emotion": "neutral",
                    "intensity": 0.5,
                    "content": content_type or "UNKNOWN",
                    "content_conf": content_confidence or 0.0,
                    "content_details": content_details,
                    "timestamp": datetime.now().isoformat()
                }
            
            # ✅ Only save VALID emotions to database
            invalid_emotions = ['error', 'no_face', 'unknown']
            should_save = emotion_data["emotion"] not in invalid_emotions
            
            if should_save:
                try:
                    emotion_log = EmotionLog(
                        user_id=current_user.id,
                        username=username,
                        emotion=emotion_data["emotion"],
                        intensity=emotion_data["intensity"],
                        content_type=content_type,
                        content_confidence=content_confidence,
                        probabilities=json.dumps(emotion_data.get("probabilities", {})),
                        is_guest=is_guest
                    )
                    db.add(emotion_log)
                    
                    if not is_guest:
                        user = db.query(User).filter(User.id == current_user.id).first()
                        if user:
                            user.current_emotion = emotion_data["emotion"]
                            user.current_emotion_intensity = emotion_data["intensity"]
                            user.current_content = content_type
                            user.last_activity = datetime.now(timezone.utc)
                            user.is_recording = True
                    
                    db.commit()
                    print(f"✅ Logged: {username} - {emotion_data['emotion']} | {activity} on {content_type}")
                except Exception as e:
                    print(f"❌ Failed to save emotion log: {e}")
                    db.rollback()
            else:
                # Still commit content session even if emotion is invalid
                try:
                    db.commit()
                except Exception:
                    pass
                print(f"⏭️ Skipping emotion save for: {emotion_data['emotion']}")
            
            return emotion_data
            
        except Exception as e:
            logger.error(f"Frame analysis error: {e}")
    
    # ✅ Commit the content session even if no camera frame
    try:
        db.commit()
    except Exception:
        pass
    
    return {
        "emotion": "neutral",
        "intensity": 0.5,
        "content": content_type or "UNKNOWN",
        "content_conf": content_confidence or 0.0,
        "content_details": content_details,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/analyze/content")
async def analyze_content_only(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze screen content only (without emotion detection).
    Uses the Screen Classifier to detect:
    - App/Website category (200+ apps)
    - Activity type (CODING, READING, WATCHING, etc.)
    - Productivity level (PRODUCTIVE, NEUTRAL, UNPRODUCTIVE)
    - Sentiment analysis
    - OCR text extraction
    - Language detection & translation
    """
    
    is_guest = getattr(current_user, 'is_guest', False)
    username = getattr(current_user, 'username', 'guest')
    
    if not is_guest:
        username = EncryptionService.decrypt_data(current_user.username_encrypted)
    
    # Try to get content analyzer (lazy load)
    analyzer = get_content_analyzer()
    if not analyzer:
        return {
            "status": "unavailable",
            "message": "Content classifier not available",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        result = analyzer.analyze()
        
        # Convert confidence string to float
        confidence_map = {'Very High': 0.95, 'High': 0.80, 'Medium': 0.60, 'Low': 0.40}
        confidence = confidence_map.get(result.get('confidence', 'Low'), 0.40)
        
        response = {
            "status": "success",
            "app_name": result.get('app_name', ''),
            "window_title": result.get('window_title', ''),
            "visual_description": result.get('visual_description', ''),
            "ocr_text": result.get('ocr_text', ''),
            "category": result.get('category', 'OTHER'),
            "category_emoji": result.get('emoji', '🏷️'),
            "confidence": confidence,
            "confidence_level": result.get('confidence', 'Low'),
            "analysis_source": result.get('analysis_source', 'unknown'),
            "language": {
                "detected": result.get('original_language', 'English'),
                "was_translated": result.get('was_translated', False),
                "translated_title": result.get('translated_title')
            },
            "sentiment": {
                "label": result.get('sentiment', 'NEUTRAL'),
                "score": result.get('sentiment_score', 0.5),
                "emoji": result.get('sentiment_emoji', '😐')
            },
            "activity": {
                "type": result.get('activity', 'UNKNOWN'),
                "emoji": result.get('activity_emoji', '🏷️'),
                "confidence": result.get('activity_confidence', 'Low')
            },
            "productivity": {
                "classification": result.get('productivity', 'NEUTRAL'),
                "emoji": result.get('productivity_emoji', '➖'),
                "confidence": result.get('productivity_confidence', 'Low'),
                "reason": result.get('productivity_reason', '')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Content analyzed for {username}: {result.get('category')} - {result.get('activity')}")
        return response
        
    except Exception as e:
        logger.error(f"Content analysis error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/content/status")
def get_content_classifier_status():
    """Check if the content classifier is available and its capabilities"""
    return {
        "available": CONTENT_CLASSIFIER_AVAILABLE,
        "features": {
            "window_detection": True,
            "visual_classification": CONTENT_CLASSIFIER_AVAILABLE,
            "ocr": CONTENT_CLASSIFIER_AVAILABLE,
            "sentiment_analysis": CONTENT_CLASSIFIER_AVAILABLE,
            "language_detection": CONTENT_CLASSIFIER_AVAILABLE,
            "activity_classification": CONTENT_CLASSIFIER_AVAILABLE,
            "productivity_scoring": CONTENT_CLASSIFIER_AVAILABLE
        },
        "supported_categories": [
            "CODING/DEVELOPMENT", "VIDEO/STREAMING", "SOCIAL MEDIA", "GAMING",
            "DOCUMENT/PRODUCTIVITY", "COMMUNICATION", "MUSIC", "IMAGE/DESIGN",
            "FILE MANAGEMENT", "NEWS", "EDUCATION", "SHOPPING", "FINANCE",
            "AI ASSISTANT", "DATABASE", "DEVOPS", "API TESTING", "SYSTEM", "UTILITIES"
        ],
        "supported_activities": [
            "WRITING", "READING", "WATCHING", "CODING", "BROWSING", "GAMING",
            "DESIGNING", "COMMUNICATING", "LISTENING", "SEARCHING", "SHOPPING", "LEARNING"
        ],
        "apps_database": "200+ apps and websites"
    }


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


# ==================== CONTENT SESSION ENDPOINTS ====================

@app.get("/api/content/sessions")
def get_content_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get content consumption session history for the current user.
    Each session shows what the user was doing, for how long, and the content type.
    """
    sessions = db.query(ContentSession).filter(
        ContentSession.user_id == current_user.id
    ).order_by(ContentSession.started_at.desc()).offset(offset).limit(limit).all()
    
    return [
        {
            "id": s.id,
            "content_type": s.content_type,
            "activity": s.activity,
            "activity_emoji": s.activity_emoji,
            "activity_confidence": s.activity_confidence,
            "productivity": s.productivity,
            "productivity_emoji": s.productivity_emoji,
            "app_name": s.app_name,
            "window_title": s.window_title,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "duration_seconds": s.duration_seconds,
            "duration_formatted": _format_duration(s.duration_seconds),
            "is_active": s.is_active,
        }
        for s in sessions
    ]


@app.get("/api/content/sessions/summary")
def get_content_sessions_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hours: int = 24
):
    """
    Get a summary of content consumption for the last N hours.
    Groups by content_type and activity, showing total time spent on each.
    """
    from sqlalchemy import func as sqla_func
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Summarize by content type
    content_summary = db.query(
        ContentSession.content_type,
        sqla_func.sum(ContentSession.duration_seconds).label('total_seconds'),
        sqla_func.count(ContentSession.id).label('session_count')
    ).filter(
        ContentSession.user_id == current_user.id,
        ContentSession.started_at >= cutoff,
        ContentSession.duration_seconds.isnot(None)
    ).group_by(ContentSession.content_type).all()
    
    # Summarize by activity
    activity_summary = db.query(
        ContentSession.activity,
        ContentSession.activity_emoji,
        sqla_func.sum(ContentSession.duration_seconds).label('total_seconds'),
        sqla_func.count(ContentSession.id).label('session_count')
    ).filter(
        ContentSession.user_id == current_user.id,
        ContentSession.started_at >= cutoff,
        ContentSession.duration_seconds.isnot(None)
    ).group_by(ContentSession.activity, ContentSession.activity_emoji).all()
    
    # Summarize by productivity
    productivity_summary = db.query(
        ContentSession.productivity,
        ContentSession.productivity_emoji,
        sqla_func.sum(ContentSession.duration_seconds).label('total_seconds'),
        sqla_func.count(ContentSession.id).label('session_count')
    ).filter(
        ContentSession.user_id == current_user.id,
        ContentSession.started_at >= cutoff,
        ContentSession.duration_seconds.isnot(None)
    ).group_by(ContentSession.productivity, ContentSession.productivity_emoji).all()
    
    total_seconds = sum(row.total_seconds or 0 for row in content_summary)
    
    return {
        "period_hours": hours,
        "total_time_seconds": total_seconds,
        "total_time_formatted": _format_duration(total_seconds),
        "by_content_type": [
            {
                "content_type": row.content_type,
                "total_seconds": row.total_seconds,
                "total_formatted": _format_duration(row.total_seconds),
                "session_count": row.session_count,
                "percentage": round((row.total_seconds / total_seconds * 100), 1) if total_seconds > 0 else 0
            }
            for row in content_summary
        ],
        "by_activity": [
            {
                "activity": row.activity,
                "activity_emoji": row.activity_emoji,
                "total_seconds": row.total_seconds,
                "total_formatted": _format_duration(row.total_seconds),
                "session_count": row.session_count,
                "percentage": round((row.total_seconds / total_seconds * 100), 1) if total_seconds > 0 else 0
            }
            for row in activity_summary
        ],
        "by_productivity": [
            {
                "productivity": row.productivity,
                "productivity_emoji": row.productivity_emoji,
                "total_seconds": row.total_seconds,
                "total_formatted": _format_duration(row.total_seconds),
                "session_count": row.session_count,
                "percentage": round((row.total_seconds / total_seconds * 100), 1) if total_seconds > 0 else 0
            }
            for row in productivity_summary
        ],
    }


@app.get("/api/content/sessions/active")
def get_active_content_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's currently active content session (what they're doing right now)."""
    session = db.query(ContentSession).filter(
        ContentSession.user_id == current_user.id,
        ContentSession.is_active == True
    ).order_by(ContentSession.started_at.desc()).first()
    
    if not session:
        return {"active": False, "session": None}
    
    now = datetime.now(timezone.utc)
    elapsed = int((now - session.started_at).total_seconds()) if session.started_at else 0
    
    return {
        "active": True,
        "session": {
            "id": session.id,
            "content_type": session.content_type,
            "activity": session.activity,
            "activity_emoji": session.activity_emoji,
            "productivity": session.productivity,
            "productivity_emoji": session.productivity_emoji,
            "app_name": session.app_name,
            "window_title": session.window_title,
            "started_at": session.started_at.isoformat(),
            "elapsed_seconds": elapsed,
            "elapsed_formatted": _format_duration(elapsed),
        }
    }


def _format_duration(seconds) -> str:
    """Format seconds into human-readable duration string."""
    if not seconds or seconds <= 0:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


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


@app.get("/api/admin/active-users")
def admin_get_active_users(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin: Get currently active users with their real-time emotions"""
    from datetime import timedelta
    
    # Users active in the last 5 minutes are considered "currently using"
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    active_users = db.query(User).filter(
        User.last_activity != None,
        User.last_activity >= cutoff_time
    ).all()
    
    return {
        "active_count": len(active_users),
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "username": EncryptionService.decrypt_data(u.username_encrypted),
                "current_emotion": u.current_emotion or "N/A",
                "current_emotion_intensity": u.current_emotion_intensity or 0,
                "current_content": u.current_content or "N/A",
                "last_activity": u.last_activity.isoformat() if u.last_activity else None,
                "status": "Recording" if getattr(u, 'is_recording', False) else "Idle"
            }
            for u in active_users
        ]
    }


@app.get("/api/dashboard/status")
def get_dashboard_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current dashboard status - OPTIMIZED for high-frequency polling"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    
    if is_guest or current_user.id == 0:
        return {
            "current_emotion": None,
            "current_emotion_intensity": None,
            "current_content": None,
            "status": "Idle",
            "last_session": None,
            "session_summary": None
        }
    
    try:
        # Use a single efficient query to get both user and last log
        # Don't use db.expire_all() - it causes extra queries
        from sqlalchemy.orm import joinedload
        
        user = db.query(User).filter(User.id == current_user.id).first()
        
        # Get only the LATEST emotion log (limit 1 - very fast)
        last_log = db.query(EmotionLog).filter(
            EmotionLog.user_id == current_user.id
        ).order_by(EmotionLog.created_at.desc()).limit(1).first()
        
        # Get the active content session for richer dashboard data
        active_session = db.query(ContentSession).filter(
            ContentSession.user_id == current_user.id,
            ContentSession.is_active == True
        ).order_by(ContentSession.started_at.desc()).limit(1).first()
        
        # Determine status
        is_recording = getattr(user, 'is_recording', False) if user else False
        status = "Recording" if is_recording else "Idle"
        
        # Get emotion/content from last_log (most reliable source)
        if last_log:
            emotion = last_log.emotion
            emotion_intensity = last_log.intensity
            content = last_log.content_type
        else:
            emotion = None
            emotion_intensity = None
            content = None
        
        # Build content details from active session
        content_details = None
        if active_session:
            # Prefer active session content over EmotionLog (more detailed)
            if not content or content == 'UNKNOWN':
                content = active_session.content_type
            content_details = {
                'activity': active_session.activity,
                'activity_emoji': active_session.activity_emoji,
                'productivity': active_session.productivity,
                'productivity_emoji': active_session.productivity_emoji,
                'app_name': active_session.app_name,
                'duration_seconds': active_session.duration_seconds or 0,
            }
        
        # Debug (reduced frequency)
        print(f"📊 Dashboard: user={current_user.id}, recording={is_recording}, emotion={emotion}, content={content}, activity={content_details.get('activity') if content_details else None}")
        
        return {
            "current_emotion": emotion,
            "current_emotion_intensity": emotion_intensity,
            "current_content": content,
            "content_details": content_details,
            "status": status,
            "last_session": last_log.created_at.isoformat() if last_log else None,
            "session_summary": None  # Moved to separate endpoint for performance
        }
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return {
            "current_emotion": None,
            "current_emotion_intensity": None,
            "current_content": None,
            "status": "Idle",
            "last_session": None,
            "session_summary": None
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


@app.get("/api/admin/audit-logs")
def admin_get_audit_logs(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
    action: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """Admin: Get detailed audit logs with filtering"""
    from sqlalchemy import desc
    
    print(f"📋 Audit logs request - action: {action}, status: {status}, limit: {limit}")
    
    query = db.query(AuditLog)
    
    # Apply filters
    if action:
        print(f"   Filtering by action: {action.upper()}")
        query = query.filter(AuditLog.action == action.upper())
    if status:
        query = query.filter(AuditLog.status == status)
    
    # Get total count
    total_count = query.count()
    print(f"   Found {total_count} audit logs")
    
    # Get paginated results
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    
    def safe_parse_json(details_str):
        """Safely parse JSON details, handling empty strings and invalid JSON"""
        if not details_str or details_str.strip() == '':
            return None
        try:
            return json.loads(details_str)
        except (json.JSONDecodeError, TypeError):
            return details_str  # Return as plain string if not valid JSON
    
    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "details": safe_parse_json(log.details),
                "ip_address": log.ip_address,
                "status": log.status,
                "timestamp": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


@app.get("/api/admin/audit-logs/summary")
def admin_get_audit_summary(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin: Get audit log summary statistics"""
    from sqlalchemy import func
    from datetime import date, timedelta
    
    # Count by action type
    action_counts = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    ).group_by(AuditLog.action).all()
    
    # Count by status
    status_counts = db.query(
        AuditLog.status,
        func.count(AuditLog.id).label('count')
    ).group_by(AuditLog.status).all()
    
    # Activity by day (last 7 days)
    today = date.today()
    daily_activity = []
    for i in range(7):
        day = today - timedelta(days=i)
        count = db.query(AuditLog).filter(
            func.date(AuditLog.created_at) == day
        ).count()
        daily_activity.append({
            "date": day.isoformat(),
            "count": count
        })
    
    # Recent failed actions
    failed_actions = db.query(AuditLog).filter(
        AuditLog.status == "failed"
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    
    def safe_parse_json(details_str):
        """Safely parse JSON details, handling empty strings and invalid JSON"""
        if not details_str or details_str.strip() == '':
            return None
        try:
            return json.loads(details_str)
        except (json.JSONDecodeError, TypeError):
            return details_str  # Return as plain string if not valid JSON
    
    return {
        "total_events": db.query(AuditLog).count(),
        "action_breakdown": {a: c for a, c in action_counts},
        "status_breakdown": {s: c for s, c in status_counts},
        "daily_activity": daily_activity,
        "recent_failures": [
            {
                "id": log.id,
                "username": log.username,
                "action": log.action,
                "details": safe_parse_json(log.details),
                "timestamp": log.created_at.isoformat() if log.created_at else None
            }
            for log in failed_actions
        ]
    }


# ==================== RECOMMENDATIONS API ====================

WELLNESS_RECOMMENDATIONS = {
    "stressed": [
        {
            "title": "Take a 5-minute break",
            "description": "Step away from your screen and take some deep breaths. Your stress levels have been elevated.",
            "priority": "High",
            "icon": "self_improvement",
            "action": "Start a guided breathing exercise"
        },
        {
            "title": "Practice 4-7-8 Breathing",
            "description": "Inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds. This activates your relaxation response.",
            "priority": "High",
            "icon": "air",
            "action": "Start breathing exercise"
        },
        {
            "title": "Progressive Muscle Relaxation",
            "description": "Tense and release each muscle group to release physical tension from stress.",
            "priority": "Medium",
            "icon": "accessibility_new",
            "action": "View exercise guide"
        }
    ],
    "anxious": [
        {
            "title": "Ground yourself with 5-4-3-2-1",
            "description": "Notice 5 things you see, 4 you feel, 3 you hear, 2 you smell, and 1 you taste.",
            "priority": "High",
            "icon": "nature",
            "action": "Start grounding exercise"
        },
        {
            "title": "Take slow, deep breaths",
            "description": "Slow your breathing to calm your nervous system and reduce anxiety.",
            "priority": "High",
            "icon": "air",
            "action": "Start breathing exercise"
        }
    ],
    "angry": [
        {
            "title": "Step away for a moment",
            "description": "Take a brief break to cool down before responding to the situation.",
            "priority": "High",
            "icon": "directions_walk",
            "action": "Set a 5-minute timer"
        },
        {
            "title": "Physical release",
            "description": "Do some stretches or light exercise to release the physical tension of anger.",
            "priority": "Medium",
            "icon": "fitness_center",
            "action": "View stretch routine"
        }
    ],
    "sad": [
        {
            "title": "Reach out to someone",
            "description": "Consider talking to a friend or loved one. Social connection can help lift your mood.",
            "priority": "High",
            "icon": "people",
            "action": "Open contacts"
        },
        {
            "title": "Take a brief walk",
            "description": "Light physical activity and fresh air can help improve your mood.",
            "priority": "Medium",
            "icon": "directions_walk",
            "action": "Set activity reminder"
        },
        {
            "title": "Listen to uplifting music",
            "description": "Music can positively influence your emotional state.",
            "priority": "Low",
            "icon": "music_note",
            "action": "Open music player"
        }
    ],
    "tired": [
        {
            "title": "Take a power nap",
            "description": "A 15-20 minute nap can help restore alertness without affecting nighttime sleep.",
            "priority": "High",
            "icon": "hotel",
            "action": "Set 20-minute timer"
        },
        {
            "title": "Get some fresh air",
            "description": "Step outside briefly. Fresh air and natural light can boost energy levels.",
            "priority": "Medium",
            "icon": "nature",
            "action": "Set reminder"
        },
        {
            "title": "Stay hydrated",
            "description": "Dehydration can cause fatigue. Drink a glass of water.",
            "priority": "Medium",
            "icon": "local_drink",
            "action": "Log water intake"
        }
    ],
    "focused": [
        {
            "title": "Maintain your focus",
            "description": "You're in a great flow state! Consider using the Pomodoro technique.",
            "priority": "Low",
            "icon": "timer",
            "action": "Start Pomodoro timer"
        }
    ],
    "happy": [
        {
            "title": "Capture this moment",
            "description": "Take note of what's making you happy. Gratitude journaling enhances well-being.",
            "priority": "Low",
            "icon": "edit_note",
            "action": "Open journal"
        }
    ],
    "neutral": [
        {
            "title": "Stay hydrated",
            "description": "Drink water regularly to maintain energy and focus.",
            "priority": "Low",
            "icon": "local_drink",
            "action": "Log water intake"
        },
        {
            "title": "Stretch your body",
            "description": "Regular stretching helps prevent tension buildup.",
            "priority": "Low",
            "icon": "accessibility_new",
            "action": "View stretch routine"
        }
    ]
}


@app.get("/api/recommendations")
def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations based on emotional patterns"""
    
    is_guest = getattr(current_user, 'is_guest', False)
    
    if is_guest or current_user.id == 0:
        # Return general recommendations for guests
        return {
            "recommendations": WELLNESS_RECOMMENDATIONS.get("neutral", []),
            "trigger_emotion": None,
            "trigger_reason": "General wellness tips"
        }
    
    # Get recent emotion logs (last hour)
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    recent_logs = db.query(EmotionLog).filter(
        EmotionLog.user_id == current_user.id,
        EmotionLog.created_at >= one_hour_ago
    ).order_by(EmotionLog.created_at.desc()).limit(20).all()
    
    if not recent_logs:
        return {
            "recommendations": WELLNESS_RECOMMENDATIONS.get("neutral", []),
            "trigger_emotion": None,
            "trigger_reason": "No recent activity"
        }
    
    # Analyze emotion patterns
    emotion_counts = {}
    total_intensity = {}
    
    for log in recent_logs:
        emotion = log.emotion.lower()
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        total_intensity[emotion] = total_intensity.get(emotion, 0) + (log.intensity or 0.5)
    
    # Find dominant negative emotion
    negative_emotions = ['stressed', 'anxious', 'angry', 'sad', 'tired', 'fear', 'fearful']
    dominant_emotion = None
    max_score = 0
    
    for emotion in negative_emotions:
        if emotion in emotion_counts:
            # Score = count * average intensity
            avg_intensity = total_intensity[emotion] / emotion_counts[emotion]
            score = emotion_counts[emotion] * avg_intensity
            if score > max_score:
                max_score = score
                dominant_emotion = emotion
    
    # Map fear variations to anxious
    if dominant_emotion in ['fear', 'fearful']:
        dominant_emotion = 'anxious'
    
    # Get recommendations for the dominant emotion (or neutral if no negative emotions)
    trigger_emotion = dominant_emotion or 'neutral'
    recommendations = WELLNESS_RECOMMENDATIONS.get(trigger_emotion, WELLNESS_RECOMMENDATIONS['neutral'])
    
    # Determine trigger reason
    if dominant_emotion:
        count = emotion_counts.get(dominant_emotion, 0) or emotion_counts.get('fear', 0) or emotion_counts.get('fearful', 0)
        avg_intensity = (total_intensity.get(dominant_emotion, 0) / max(count, 1)) * 100
        trigger_reason = f"Detected {trigger_emotion} emotion {count} times in the last hour (avg intensity: {avg_intensity:.0f}%)"
    else:
        trigger_reason = "Based on your general wellness"
    
    return {
        "recommendations": recommendations,
        "trigger_emotion": trigger_emotion,
        "trigger_reason": trigger_reason,
        "emotion_summary": {
            emotion: {
                "count": emotion_counts.get(emotion, 0),
                "avg_intensity": (total_intensity.get(emotion, 0) / emotion_counts.get(emotion, 1)) * 100 if emotion in emotion_counts else 0
            }
            for emotion in emotion_counts
        }
    }


@app.post("/api/recommendations/trigger")
def trigger_recommendation(
    emotion: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger recommendations for a specific emotion"""
    
    if emotion:
        emotion = emotion.lower()
        if emotion in ['fear', 'fearful']:
            emotion = 'anxious'
    else:
        # Get current emotion from user
        is_guest = getattr(current_user, 'is_guest', False)
        if is_guest or current_user.id == 0:
            emotion = 'neutral'
        else:
            user = db.query(User).filter(User.id == current_user.id).first()
            emotion = (user.current_emotion or 'neutral').lower()
    
    recommendations = WELLNESS_RECOMMENDATIONS.get(emotion, WELLNESS_RECOMMENDATIONS['neutral'])
    
    return {
        "recommendations": recommendations,
        "trigger_emotion": emotion,
        "trigger_reason": f"Manually triggered for {emotion} state"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)