from database import engine
from sqlalchemy import text

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN current_emotion VARCHAR(50)"))
            print("Added current_emotion column")
        except Exception as e:
            print(f"Error adding current_emotion: {e}")
            
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN current_emotion_intensity FLOAT"))
            print("Added current_emotion_intensity column")
        except Exception as e:
            print(f"Error adding current_emotion_intensity: {e}")
        
        conn.commit()

if __name__ == "__main__":
    add_columns()
