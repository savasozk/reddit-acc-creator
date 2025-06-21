from cryptography.fernet import Fernet
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.config import settings

# Initialize Argon2 password hasher
ph = PasswordHasher()


def generate_encryption_key() -> bytes:
    """Generates a new Fernet encryption key and saves it to a file."""
    key = Fernet.generate_key()
    with open(settings.encryption_key_file, "wb") as key_file:
        key_file.write(key)
    return key


def load_encryption_key() -> bytes:
    """
    Loads the encryption key from the file specified in settings.
    If the file doesn't exist, it generates a new key.
    """
    try:
        with open(settings.encryption_key_file, "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        return generate_encryption_key()


def encrypt_data(data: str) -> bytes:
    """Encrypts a string using the application's Fernet key."""
    key = load_encryption_key()
    f = Fernet(key)
    return f.encrypt(data.encode('utf-8'))


def decrypt_data(encrypted_data: bytes) -> str:
    """Decrypts data using the application's Fernet key."""
    key = load_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode('utf-8')


def hash_password(password: str) -> str:
    """Hashes a password using Argon2."""
    return ph.hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    """Verifies a password against an Argon2 hash."""
    try:
        ph.verify(hashed_password, password)
        return True
    except VerifyMismatchError:
        return False 