from cryptography.fernet import Fernet
from passlib.context import CryptContext
from config import settings
import base64
import hashlib
import logging
import warnings

logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore', message='.*bcrypt version.*')

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

try:
    fernet = Fernet(settings.ENCRYPTION_KEY.encode())
except Exception as e:
    logger.error(f"Failed to initialize Fernet: {e}")
    fernet = Fernet(Fernet.generate_key())
    logger.warning("Using auto-generated encryption key")


class EncryptionService:
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using Argon2 (one-way)"""
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Password hashing error: {e}")
            raise ValueError("Failed to hash password")
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def hash_username(username: str) -> str:
        """
        Hash username deterministically for lookup (SHA-256)
        Unlike Fernet, SHA-256 produces the same output for the same input
        """
        return hashlib.sha256(username.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_email(email: str) -> str:
        """
        Hash email deterministically for lookup (SHA-256)
        Same as username hashing - produces consistent output for same input
        """
        return hashlib.sha256(email.encode('utf-8')).hexdigest()
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encrypt sensitive data (two-way) - for display purposes"""
        try:
            encrypted_bytes = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError("Failed to encrypt data")
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Decrypt encrypted data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError("Failed to decrypt data")
    
    @staticmethod
    def generate_encryption_key() -> str:
        """Generate new Fernet key"""
        return Fernet.generate_key().decode()


if __name__ == "__main__":
    print("="*50)
    print("🔐 ENCRYPTION KEY GENERATOR")
    print("="*50)
    key = EncryptionService.generate_encryption_key()
    print(f"\n✅ Your Encryption Key:\n{key}")
    print(f"\n📝 Copy this to your .env file:")
    print(f"ENCRYPTION_KEY={key}")
    print("\n" + "="*50)
    
    # Test username hashing
    print("\n🧪 Testing username hashing...")
    username = "johndoe"
    hash1 = EncryptionService.hash_username(username)
    hash2 = EncryptionService.hash_username(username)
    print(f"Username: {username}")
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Are they equal? {'✅ Yes' if hash1 == hash2 else '❌ No'}")
    
    # Test email hashing
    print("\n🧪 Testing email hashing...")
    email = "test@example.com"
    email_hash1 = EncryptionService.hash_email(email)
    email_hash2 = EncryptionService.hash_email(email)
    print(f"Email: {email}")
    print(f"Hash 1: {email_hash1}")
    print(f"Hash 2: {email_hash2}")
    print(f"Are they equal? {'✅ Yes' if email_hash1 == email_hash2 else '❌ No'}")