from database import SessionLocal
from models import EmotionLog
from sqlalchemy import desc

def check_emotions():
    db = SessionLocal()
    try:
        emotions = db.query(EmotionLog).order_by(desc(EmotionLog.created_at)).all()
        print(f"Found {len(emotions)} emotion logs:")
        print("-" * 80)
        print(f"{'ID':<5} | {'User':<20} | {'Emotion':<15} | {'Intensity':<10} | {'Time':<25}")
        print("-" * 80)
        for log in emotions:
            print(f"{log.id:<5} | {log.username:<20} | {log.emotion:<15} | {log.intensity:<10.2f} | {str(log.created_at):<25}")
    finally:
        db.close()

if __name__ == "__main__":
    check_emotions()
