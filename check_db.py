from database import SessionLocal
from models import User, EmotionLog

db = SessionLocal()
user = db.query(User).first()

if user:
    print(f"User ID: {user.id}")
    print(f"is_recording: {user.is_recording}")
    print(f"current_emotion: {user.current_emotion}")
    print(f"current_content: {user.current_content}")
else:
    print("No user found")

logs = db.query(EmotionLog).order_by(EmotionLog.created_at.desc()).limit(5).all()
print(f"\nTotal logs found: {len(logs)}")
for l in logs:
    print(f"  {l.emotion} ({l.intensity:.2f}) - content: {l.content_type}")

db.close()
