"""
Migration script: Add content_sessions table for activity tracking + time duration.
Run this once to create the new table in the existing database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename='content_sessions'"
        ))
        if result.fetchone():
            print("✅ content_sessions table already exists, skipping.")
            return

        conn.execute(text("""
            CREATE TABLE content_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username VARCHAR(255) NOT NULL,
                
                content_type VARCHAR(50) NOT NULL,
                content_confidence FLOAT,
                
                activity VARCHAR(50) NOT NULL,
                activity_emoji VARCHAR(10),
                activity_confidence VARCHAR(20),
                
                productivity VARCHAR(20),
                productivity_emoji VARCHAR(10),
                
                app_name VARCHAR(100),
                window_title VARCHAR(500),
                
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                
                is_active BOOLEAN DEFAULT TRUE,
                is_guest BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create indexes for fast lookups
        conn.execute(text("CREATE INDEX ix_content_sessions_user_id ON content_sessions (user_id)"))
        conn.execute(text("CREATE INDEX ix_content_sessions_content_type ON content_sessions (content_type)"))
        conn.execute(text("CREATE INDEX ix_content_sessions_activity ON content_sessions (activity)"))
        conn.execute(text("CREATE INDEX ix_content_sessions_started_at ON content_sessions (started_at)"))

        conn.commit()
        print("✅ content_sessions table created successfully!")
        print("   Columns: id, user_id, username, content_type, content_confidence,")
        print("            activity, activity_emoji, activity_confidence,")
        print("            productivity, productivity_emoji,")
        print("            app_name, window_title,")
        print("            started_at, ended_at, duration_seconds,")
        print("            is_active, is_guest, created_at")


if __name__ == "__main__":
    migrate()
