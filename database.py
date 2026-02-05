from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config import settings

# Configure engine with larger connection pool for high-frequency polling
engine = create_engine(
    settings.DATABASE_URL, 
    echo=False,
    poolclass=QueuePool,
    pool_size=20,          # Increase from default 5
    max_overflow=30,       # Increase from default 10
    pool_timeout=60,       # Increase timeout
    pool_recycle=1800,     # Recycle connections after 30 min
    pool_pre_ping=True     # Check connection is alive before using
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()