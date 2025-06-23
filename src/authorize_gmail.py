import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow
from loguru import logger

# Add project root to path to allow sibling imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import settings


def main():
    """
    Runs the OAuth 2.0 flow to get user consent and credentials.
    This is a one-time, interactive process to generate the token.json file,
    which stores the refresh token needed for non-interactive authentication.
    """
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    logger.info("Starting Gmail authorization process...")

    creds_file = settings.gmail_credentials_file
    token_file = settings.gmail_token_file
    scopes = settings.gmail_scopes

    if not creds_file or not os.path.exists(creds_file):
        logger.error(f"Error: Credentials file not found at '{creds_file}'.")
        logger.error("Please ensure you have uploaded your 'credentials.json' file via the UI and saved the configuration.")
        sys.exit(1)

    logger.info(f"Using credentials from: {creds_file}")
    logger.info(f"Using scopes: {scopes}")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, scopes)

        # The port must match the one specified in the "Authorized redirect URIs"
        # in your Google Cloud Platform project for this OAuth 2.0 client ID.
        # For a desktop app, it's typically a loopback address.
        creds = flow.run_local_server(
            port=0,
            prompt='consent',
            authorization_prompt_message='Please visit this URL to authorize this application: {url}'
        )

        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

        logger.success(f"Authorization successful! Token saved to: {token_file}")
        logger.info("You can now close the browser tab and this window.")

    except FileNotFoundError:
        logger.error(f"FATAL: The credentials file '{creds_file}' was not found.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during authorization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 