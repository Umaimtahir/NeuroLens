import asyncio
import sys
import os

# Add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from models import User, EmotionLog
from main import analyze_frame
from fastapi import UploadFile
import datetime
import cv2
import numpy as np

# Mock UploadFile
class MockUploadFile:
    def __init__(self, data):
        self.data = data
    async def read(self):
        return self.data

# Ensure tables exist
Base.metadata.create_all(bind=engine)

from encryption import EncryptionService

async def reproduce():
    db = SessionLocal()
    try:
        # Delete existing test user to ensure clean state
        existing_user = db.query(User).filter(User.username_hash == "test_user_hash").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
            
        encrypted_email = EncryptionService.encrypt_data("test@example.com")
        encrypted_username = EncryptionService.encrypt_data("test_user")
        
        user = User(
            name="Test User",
            email_encrypted=encrypted_email,
            email_hash="test_email_hash",
            username_hash="test_user_hash",
            username_encrypted=encrypted_username,
            password_hash="hash",
            email_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"User ID: {user.id}")

        # Call analyze_frame (WITH frame)
        print("Calling analyze_frame with dummy frame...")
        
        # Create a dummy image (black square)
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        # Draw a face-like rectangle to trigger detection (maybe)
        cv2.rectangle(img, (20, 20), (80, 80), (255, 255, 255), -1)
        
        success, encoded_img = cv2.imencode('.jpg', img)
        frame_bytes = encoded_img.tobytes()
        
        result = await analyze_frame(frame=MockUploadFile(frame_bytes), current_user=user, db=db)
        print(f"Result: {result}")

        # Check database
        log = db.query(EmotionLog).filter(EmotionLog.user_id == user.id).order_by(EmotionLog.created_at.desc()).first()
        
        if log:
            print("✅ EmotionLog found!")
            print(f"ID: {log.id}, Emotion: {log.emotion}, Created At: {log.created_at}")
        else:
            print("❌ No EmotionLog found!")
            
        # Check User current emotion
        db.refresh(user)
        if user.current_emotion:
            print(f"✅ User current_emotion found: {user.current_emotion} ({user.current_emotion_intensity})")
        else:
            print("❌ User current_emotion NOT found!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(reproduce())
