import os
import base64
import toml
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field
from loguru import logger

# Define file paths
CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.toml")
ENCRYPTED_CONFIG_FILE = os.path.join(CONFIG_DIR, "config.encrypted.toml")
GMAIL_CREDS_FILE = os.path.join(CONFIG_DIR, "gmail_credentials.json")
PROFILES_OUTPUT_FILE = os.path.join("output", "profiles.json")


# --- Pydantic Models for Type-Safe Config ---

class CaptchaConfig(BaseModel):
    caps_key: str = ""
    captcha_2_key: Optional[str] = None
    retries: int = 3

class AdsPowerConfig(BaseModel):
    base_url: str = "http://127.0.0.1:50325"
    access_token: Optional[str] = None
    group_id: str = ""

class GmailConfig(BaseModel):
    credentials_json: Optional[str] = None # Will store the content of the uploaded file
    # Paths to other files will be derived from the main config dir
    token_file: str = Field(default=os.path.join(CONFIG_DIR, "token.json"))
    encrypted_refresh_token_file: str = Field(default=os.path.join(CONFIG_DIR, "encrypted_refresh_token.bin"))
    encryption_key_file: str = Field(default=os.path.join(CONFIG_DIR, ".gmail.key")) # Separate key for gmail creds
    scopes: list[str] = Field(default=["https://www.googleapis.com/auth/gmail.readonly"])

class DataImpulseConfig(BaseModel):
    user: Optional[str] = None
    password: Optional[str] = None

class AppConfig(BaseModel):
    captcha: CaptchaConfig = Field(default_factory=CaptchaConfig)
    adspower: AdsPowerConfig = Field(default_factory=AdsPowerConfig)
    gmail: GmailConfig = Field(default_factory=GmailConfig)
    dataimpulse: DataImpulseConfig = Field(default_factory=DataImpulseConfig)
    rotation_interval_minutes: int = 60


# --- Encryption and Loading/Saving Logic ---

def get_key_from_password(password: str, salt: bytes) -> bytes:
    """Derives a Fernet key from a master password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def save_config(config: AppConfig, master_password: str) -> None:
    """Encrypts and saves the configuration to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Save the Gmail credentials JSON to its own file if it exists
    if config.gmail.credentials_json:
        with open(GMAIL_CREDS_FILE, "w") as f:
            f.write(config.gmail.credentials_json)
        # Don't store the large JSON string in the main config file
        config.gmail.credentials_json = None

    config_data = config.model_dump_json(indent=4)
    salt = os.urandom(16)
    key = get_key_from_password(master_password, salt)
    f = Fernet(key)
    encrypted_data = f.encrypt(config_data.encode())

    with open(ENCRYPTED_CONFIG_FILE, "wb") as f:
        f.write(salt + encrypted_data)
    logger.success("Configuration saved and encrypted successfully.")

def load_config(master_password: Optional[str] = None) -> Optional[AppConfig]:
    """Loads and decrypts the configuration from disk."""
    if master_password is None:
        master_password = os.getenv("MASTER_PASSWORD", "")
        
    if not master_password:
        logger.warning("Master password not provided. Cannot load config.")
        return None
        
    if not os.path.exists(ENCRYPTED_CONFIG_FILE):
        logger.warning(f"Encrypted config file not found at {ENCRYPTED_CONFIG_FILE}")
        return AppConfig() # Return default config if file doesn't exist

    try:
        with open(ENCRYPTED_CONFIG_FILE, "rb") as f:
            data = f.read()
            salt, encrypted_config = data[:16], data[16:]
        
        key = get_key_from_password(master_password, salt)
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_config)
        
        config = AppConfig.model_validate_json(decrypted_data)

        # Load Gmail credentials from separate file if it exists
        if os.path.exists(GMAIL_CREDS_FILE):
            with open(GMAIL_CREDS_FILE, "r") as f:
                config.gmail.credentials_json = f.read()
        
        logger.info("Configuration loaded and decrypted successfully.")
        return config
    except Exception as e:
        logger.error(f"Failed to load or decrypt configuration: {e}")
        return None 