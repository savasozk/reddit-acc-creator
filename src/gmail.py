import base64
import os.path
import time
from email.message import Message
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from loguru import logger

from src.config import settings
from src.security import encrypt_data, decrypt_data, get_fernet


class GmailAPI:
    """A wrapper for the Gmail API to handle email verification."""

    def __init__(self):
        """Initializes the Gmail API service."""
        self.creds = self._get_credentials()
        if not self.creds:
            # This is a fatal error for the script, as it cannot proceed.
            raise ConnectionError(
                "Gmail credentials (`token.json`) are not found or are invalid. "
                "Please go to the UI Configuration page and complete the "
                "'Authorize Gmail Account' step."
            )
        self.service = self._build_service()

    def _get_credentials(self) -> Optional[Credentials]:
        """
        Loads credentials from the token file. If expired, it tries to refresh
        them. This function is completely non-interactive.
        """
        creds = None
        token_file = settings.gmail_token_file

        if not os.path.exists(token_file):
            logger.warning(f"Gmail token file not found at '{token_file}'.")
            return None  # Cannot proceed without the token file.

        try:
            creds = Credentials.from_authorized_user_file(token_file, settings.gmail_scopes)
        except Exception as e:
            logger.error(f"Failed to load credentials from '{token_file}': {e}")
            return None

        # If credentials are not valid, try to refresh them.
        if creds and not creds.valid:
            logger.info("Gmail credentials are not valid. Attempting to refresh...")
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Persist the refreshed credentials
                    with open(token_file, "w") as token:
                        token.write(creds.to_json())
                    logger.success("Gmail token refreshed and saved successfully.")
                except RefreshError as e:
                    logger.error(f"Failed to refresh Gmail token: {e}")
                    logger.error(
                        "The refresh token may be expired or revoked. "
                        "Please re-authorize the application via the UI."
                    )
                    # Invalidate credentials if refresh fails
                    return None
            else:
                logger.warning("Credentials have expired and no refresh token is available.")
                return None

        return creds

    def _build_service(self) -> Optional[Resource]:
        """Builds the Gmail service resource."""
        if not self.creds:
            logger.error("Could not obtain credentials for Gmail API.")
            return None
        try:
            service = build("gmail", "v1", credentials=self.creds)
            logger.info("Gmail API service built successfully.")
            return service
        except HttpError as error:
            logger.error(f"An error occurred building Gmail service: {error}")
            return None

    def find_verification_link(self, after_timestamp: int) -> Optional[str]:
        """
        Searches for a Reddit verification email and extracts the link.

        Args:
            after_timestamp: A Unix timestamp. Only emails received after this time
                             will be searched.

        Returns:
            The verification link, or None if not found.
        """
        if not self.service:
            return None

        time.sleep(15) # Give email a moment to arrive

        query = f"from:noreply@reddit.com subject:\"Verify your Reddit email address\" after:{after_timestamp}"
        
        for _ in range(5): # Retry a few times
            try:
                results = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=1)
                    .execute()
                )
                messages = results.get("messages", [])

                if not messages:
                    logger.info("No new Reddit verification email found. Waiting...")
                    time.sleep(10)
                    continue

                msg_id = messages[0]["id"]
                message = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                
                payload = message['payload']
                if 'parts' in payload:
                    part = payload['parts'][0]
                    data = part['body']['data']
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                    
                    # This is a simplified search. A more robust solution would parse the HTML.
                    start = html_content.find('https://www.reddit.com/verification/')
                    if start != -1:
                        end = html_content.find('"', start)
                        link = html_content[start:end]
                        logger.success(f"Found verification link: {link}")
                        return link
                
                logger.warning("Found email but could not extract verification link.")
                return None

            except HttpError as error:
                logger.error(f"An error occurred: {error}")
                break # Exit loop on API error
        
        logger.error("Could not find verification email after several attempts.")
        return None 