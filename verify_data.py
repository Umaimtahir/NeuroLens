"""Quick script to verify emotion and content data in database"""
from database import SessionLocal
from models import EmotionLog, User

db = SessionLocal()

print("=" * 60)
print("RECENT EMOTION LOGS (Last 10)")
print("=" * 60)

logs = db.query(EmotionLog).order_by(EmotionLog.created_at.desc()).limit(10).all()

for log in logs:
    print(f"ID: {log.id}")
    print(f"  User: {log.username} (ID: {log.user_id})")
    print(f"  Emotion: {log.emotion} ({log.intensity:.2f})")
    print(f"  Content: {log.content_type} ({log.content_confidence})")
    print(f"  Time: {log.created_at}")
    print("-" * 40)

print("\n" + "=" * 60)
print("USER CURRENT STATE")
print("=" * 60)

users = db.query(User).all()
for user in users:
    print(f"User ID: {user.id}, Name: {user.name}")
    print(f"  Current Emotion: {user.current_emotion}")
    print(f"  Current Content: {user.current_content}")
    print(f"  Is Recording: {user.is_recording}")
    print("-" * 40)

db.close()
print("\n✅ Done!")
