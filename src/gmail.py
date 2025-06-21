import base64
import os.path
import time
from email.message import Message
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from loguru import logger

from src.config import settings
from src.security import encrypt_data, decrypt_data


class GmailAPI:
    """A wrapper for the Gmail API to handle email verification."""

    def __init__(self):
        """Initializes the Gmail API service."""
        self.creds = self._get_credentials()
        self.service = self._build_service()

    def _get_credentials(self) -> Optional[Credentials]:
        """
        Gets user credentials. Handles refresh token encryption.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens.
        # It is created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(settings.encrypted_refresh_token_file):
            encrypted_token = open(settings.encrypted_refresh_token_file, "rb").read()
            refresh_token = decrypt_data(encrypted_token)
            # You might need to adjust this part based on how you store other creds info
            # For this example, we assume we just need the refresh token.
            # You'd typically load the full credentials JSON and then set the refresh token.
            creds = Credentials.from_authorized_user_file(settings.gmail_token_file, settings.gmail_scopes)
            creds.refresh_token = refresh_token

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_file, settings.gmail_scopes
                )
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(settings.gmail_token_file, "w") as token:
                token.write(creds.to_json())
            
            # Encrypt and save the refresh token separately
            if creds.refresh_token:
                encrypted_token = encrypt_data(creds.refresh_token)
                with open(settings.encrypted_refresh_token_file, "wb") as token_file:
                    token_file.write(encrypted_token)
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