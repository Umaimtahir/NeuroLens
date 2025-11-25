#python

from database import SessionLocal
from models import User
from encryption import EncryptionService

db = SessionLocal()
users = db.query(User).all()

print(f"Total users: {len(users)}")
for user in users:
    try:
        # Decrypt email and username (these are encrypted)
        username = EncryptionService.decrypt_data(user.username_encrypted)
        email = EncryptionService.decrypt_data(user.email_encrypted)
        # Note: password_hash is a hash, not encrypted data - cannot be decrypted
        print(f"User {user.id}: {username} ({email})")
        print(f"  Name: {user.name}")
        print(f"  Active: {user.is_active}")
        print(f"  Created: {user.created_at}")
    except Exception as e:
        print(f"User {user.id}: [decrypt error] - {str(e)}")

db.close()