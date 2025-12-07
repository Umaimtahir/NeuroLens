"""
Create admin user with specific credentials
Run this script once to create the admin user in the database.
"""
from database import SessionLocal, engine, Base
from models import User
from encryption import EncryptionService

# Create tables if not exist
Base.metadata.create_all(bind=engine)

def create_admin_user():
    db = SessionLocal()
    try:
        # Admin credentials
        admin_username = "admin"
        admin_password = "umaimtahir1$%"
        admin_email = "admin@neurolens.app"
        admin_name = "Admin"
        
        # Check if admin already exists
        username_hash = EncryptionService.hash_username(admin_username.lower())
        existing_user = db.query(User).filter(User.username_hash == username_hash).first()
        
        if existing_user:
            print("⚠️ Admin user already exists. Updating password...")
            existing_user.password_hash = EncryptionService.hash_password(admin_password)
            db.commit()
            print("✅ Admin password updated successfully!")
            print(f"   Username: {admin_username}")
            print(f"   Password: {admin_password}")
            return
        
        # Create new admin user
        email_hash = EncryptionService.hash_email(admin_email.lower())
        
        admin_user = User(
            name=admin_name,
            email_encrypted=EncryptionService.encrypt_data(admin_email),
            email_hash=email_hash,
            username_hash=username_hash,
            username_encrypted=EncryptionService.encrypt_data(admin_username),
            password_hash=EncryptionService.hash_password(admin_password),
            email_verified=True,  # Admin is pre-verified
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✅ Admin user created successfully!")
        print(f"   Username: {admin_username}")
        print(f"   Password: {admin_password}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
