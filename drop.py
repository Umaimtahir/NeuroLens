from sqlalchemy import create_engine, text

# Connect to default 'postgres' database, NOT neurolens_db
engine = create_engine("postgresql://postgres:1234@localhost:5432/postgres")

with engine.connect() as conn:
    conn.execution_options(isolation_level="AUTOCOMMIT")

    # Terminate all connections to neurolens_db
    conn.execute(text("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'neurolens_db'
          AND pid <> pg_backend_pid();
    """))

    # Drop and recreate database
    conn.execute(text("DROP DATABASE IF EXISTS neurolens_db"))
    conn.execute(text("CREATE DATABASE neurolens_db"))

print("✅ neurolens_db dropped and recreated successfully!")
