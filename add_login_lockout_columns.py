"""
Add login lockout columns to users table
Run: python add_login_lockout_columns.py
"""

from sqlalchemy import text
from database import engine

def add_login_lockout_columns():
    """Add failed_login_attempts and account_locked_until columns to users table"""
    
    with engine.connect() as conn:
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('failed_login_attempts', 'account_locked_until')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        # Add failed_login_attempts if not exists
        if 'failed_login_attempts' not in existing_columns:
            print("Adding 'failed_login_attempts' column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN failed_login_attempts INTEGER DEFAULT 0 NOT NULL
            """))
            print("✅ Added 'failed_login_attempts' column")
        else:
            print("ℹ️ 'failed_login_attempts' column already exists")
        
        # Add account_locked_until if not exists
        if 'account_locked_until' not in existing_columns:
            print("Adding 'account_locked_until' column...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN account_locked_until TIMESTAMP WITH TIME ZONE NULL
            """))
            print("✅ Added 'account_locked_until' column")
        else:
            print("ℹ️ 'account_locked_until' column already exists")
        
        conn.commit()
        print("\n✅ Migration complete!")

if __name__ == "__main__":
    add_login_lockout_columns()
