import base64
import json
import time
from unittest.mock import patch, mock_open

import pytest
from google.oauth2.credentials import Credentials

from src.gmail import GmailAPI
from src.config import settings

# Mock settings for testing
settings.gmail_credentials_file = "fake_creds.json"
settings.gmail_token_file = "fake_token.json"
settings.encrypted_refresh_token_file = "fake_encrypted_token.bin"
settings.encryption_key_file = "fake.key"


@pytest.fixture
def mock_google_api():
    """Fixture to mock the googleapiclient.discovery.build."""
    with patch("googleapiclient.discovery.build") as mock_build:
        yield mock_build


@pytest.fixture
def mock_flow():
    """Fixture to mock the OAuth2 flow."""
    with patch("google_auth_oauthlib.flow.InstalledAppFlow") as mock_flow_class:
        # Mock the instance and its run_local_server method
        mock_instance = mock_flow_class.from_client_secrets_file.return_value
        mock_instance.run_local_server.return_value = Credentials(
            token="fake_access_token",
            refresh_token="fake_refresh_token",
            scopes=settings.gmail_scopes
        )
        yield mock_flow_class


def test_gmail_api_init_and_find_link(mock_google_api, mock_flow):
    """Test GmailAPI initialization and finding a verification link."""
    # Mock the file system
    mock_file_system = {
        settings.gmail_credentials_file: '{}',
        # No initial token files exist to force the auth flow
    }
    
    # Mock the HTML content of an email
    verification_link = "https://www.reddit.com/verification/some_token"
    html_body = f'<html><body><a href="{verification_link}">Verify</a></body></html>'
    encoded_body = base64.urlsafe_b64encode(html_body.encode('utf-8')).decode('utf-8')

    # Mock the responses from the Gmail API service
    mock_service = mock_google_api.return_value
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "12345"}]
    }
    mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = {
        "payload": {"parts": [{"body": {"data": encoded_body}}]}
    }
    
    with patch("builtins.open", new_callable=mock_open, read_data=json.dumps(mock_file_system)):
        with patch("os.path.exists", side_effect=lambda path: path in mock_file_system):
            
            gmail_api = GmailAPI()
            assert gmail_api.service is not None

            link = gmail_api.find_verification_link(after_timestamp=int(time.time()))
            
            assert link == verification_link
            
            # Verify that the list and get methods were called
            mock_service.users().messages().list.assert_called_once()
            mock_service.users().messages().get.assert_called_once_with(
                userId="me", id="12345", format="full"
            )

def test_gmail_api_no_link_found(mock_google_api, mock_flow):
    """Test the case where no verification email is found."""
    mock_file_system = {settings.gmail_credentials_file: '{}'}
    mock_service = mock_google_api.return_value
    mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [] # No messages found
    }

    with patch("builtins.open", new_callable=mock_open, read_data=json.dumps(mock_file_system)):
        with patch("os.path.exists", side_effect=lambda path: path in mock_file_system):
            gmail_api = GmailAPI()
            link = gmail_api.find_verification_link(after_timestamp=int(time.time()))
            assert link is None 