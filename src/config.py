import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Manages application settings using Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # CAPTCHA Settings
    anticaptcha_key: Optional[str] = Field(
        None, description="API key for Anti-Captcha."
    )
    caps_key: Optional[str] = Field(None, description="API key for CapSolver.")
    captcha_2_key: Optional[str] = Field(
        None, description="API key for 2Captcha (fallback)."
    )
    captcha_retries: int = Field(
        3, description="Number of retries before falling back to 2Captcha."
    )

    # AdsPower Settings
    adspower_api_url: str = Field(
        "http://local.adspower.net:50325",
        description="URL for the AdsPower Local API.",
    )

    # Gmail API Settings
    gmail_credentials_file: str = Field(
        "credentials.json", description="Path to Gmail API credentials."
    )
    gmail_token_file: str = Field(
        "token.json", description="Path to store Gmail API token."
    )
    encrypted_refresh_token_file: str = Field(
        "encrypted_refresh_token.bin",
        description="Path to store the encrypted refresh token.",
    )
    encryption_key_file: str = Field(
        ".key", description="Path to the Fernet encryption key."
    )
    gmail_scopes: List[str] = Field(
        ["https://www.googleapis.com/auth/gmail.readonly"],
        description="Scopes for Gmail API access.",
    )

    # Logging Settings
    log_level: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO).")

    # Output Settings
    profiles_output_file: str = Field(
        "profiles.json", description="File to log created profiles."
    )


def get_settings() -> Settings:
    """Returns a cached instance of the Settings."""
    return Settings()


settings = get_settings() 