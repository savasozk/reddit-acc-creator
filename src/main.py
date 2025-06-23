import asyncio
import json
import random
import string
import time
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from loguru import logger
from pydantic import BaseModel, Field

from src.adspower import AdsPowerAPI
from src.browser import get_browser, get_current_ip
from src.captcha import CaptchaSolver
from src.config import settings
from src.gmail import GmailAPI
from src.security import hash_password

# --- Loguru Configuration ---
# Remove default handler to ensure all logs go to the file
logger.remove()
# Configure logger to write to a file for the UI to tail
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "profile_creator.log")
os.makedirs(LOG_DIR, exist_ok=True)
logger.add(LOG_FILE, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", rotation="10 MB", catch=True)


class RedditProfile(BaseModel):
    """A Pydantic model for storing created Reddit profile data."""
    username: str
    password_hash: str
    email: str
    creation_timestamp: float = Field(default_factory=time.time)
    adspower_profile_id: str
    status: str = "created"
    ip_on_creation: Optional[str] = None
    ip_on_verification: Optional[str] = None
    ip_rotated: bool = False
    verification_link_used: Optional[str] = None
    error_message: Optional[str] = None


def generate_random_string(length: int = 10) -> str:
    """Generates a random alphanumeric string."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def save_profile_to_json(profile: RedditProfile) -> None:
    """Appends a profile to the JSON log file."""
    output_file = Path(settings.profiles_output_file)
    try:
        # Ensure the directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if output_file.exists():
            with open(output_file, "r+") as f:
                data = json.load(f)
                data.append(profile.model_dump(mode="json"))
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=4)
        else:
            with open(output_file, "w") as f:
                json.dump([profile.model_dump(mode="json")], f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save profile to {output_file}: {e}")


async def create_single_profile(
    adspower_api: AdsPowerAPI,
    captcha_solver: CaptchaSolver,
    gmail_api: GmailAPI,
    email_address: str,
    proxy_config: Dict[str, Any],
) -> None:
    """Main orchestration logic for creating a single Reddit profile."""
    username = f"user_{generate_random_string(8)}"
    password = generate_random_string(12)
    profile_name = f"Reddit_{username}"

    # 1. Create AdsPower profile
    adspower_id = adspower_api.create_profile(
        name=profile_name,
        group_id=settings.adspower_group_id,  # Use group_id from centralized settings
        proxy_config=proxy_config,
        fingerprint_config=get_fingerprint_config(),  # Assuming a default fingerprint for now
    )
    if not adspower_id:
        logger.error("Failed to create AdsPower profile. Aborting.")
        # Optionally log this failure
        return

    profile_data = RedditProfile(
        username=username,
        password_hash=hash_password(password),
        email=email_address,
        adspower_profile_id=adspower_id,
    )

    # 2. Start browser
    browser_data = adspower_api.start_browser(user_id=adspower_id)
    if not browser_data:
        profile_data.status = "error"
        profile_data.error_message = "Failed to start browser."
        save_profile_to_json(profile_data)
        return

    # 3. Connect Zendriver
    browser = await get_browser(ws_endpoint=browser_data["ws"]["selenium"])
    if not browser:
        profile_data.status = "error"
        profile_data.error_message = "Failed to connect to browser with Zendriver."
        save_profile_to_json(profile_data)
        adspower_api.stop_browser(user_id=adspower_id)
        return

    try:
        # 4. Perform Account Creation
        page = await browser.new_page()
        profile_data.ip_on_creation = await get_current_ip(browser)

        logger.info(f"Navigating to Reddit signup for user {username}")
        await page.goto("https://www.reddit.com/account/register/", wait_until="domcontentloaded")

        # Fill in email and username
        await page.type("#regEmail", email_address)
        await page.click("button[data-step='email']")
        await asyncio.sleep(2)
        await page.type("#regUsername", username)
        await page.type("#regPassword", password)

        # Solve CAPTCHA
        captcha_iframe = await page.query_selector("iframe[src*='recaptcha']")
        if captcha_iframe:
            logger.info("CAPTCHA detected, attempting to solve.")
            site_key = captcha_iframe.get_property("src").split("k=")[1].split("&")[0]
            
            captcha_solution = await captcha_solver.solve_recaptcha_v2(
                website_url=page.url, website_key=site_key
            )

            if captcha_solution:
                await page.evaluate(
                    f"""document.getElementById('g-recaptcha-response').innerHTML='{captcha_solution}';"""
                )
                await asyncio.sleep(1)
                # You might need a more sophisticated way to trigger the callback,
                # but for many forms, setting the value is enough.
            else:
                raise Exception("Failed to solve CAPTCHA.")
        
        # Click Sign Up
        await page.click("button[data-step='username-and-password']")
        start_time = time.time() # Start timer for email search
        
        # Check for errors after submission
        await asyncio.sleep(5) # Wait for page to react
        # A more robust check would be to look for specific error messages
        
        logger.success(f"Successfully submitted registration for {username}.")

        # 5. Email Verification
        logger.info("Searching for verification email.")
        verification_link = gmail_api.find_verification_link(after_timestamp=int(start_time))

        if verification_link:
            profile_data.verification_link_used = verification_link
            logger.info(f"Navigating to verification link: {verification_link}")
            verification_page = await browser.new_page()
            await verification_page.goto(verification_link)
            profile_data.ip_on_verification = await get_current_ip(browser)
            await asyncio.sleep(3)
            await verification_page.close()
            
            if profile_data.ip_on_creation != profile_data.ip_on_verification:
                profile_data.ip_rotated = True
                logger.warning(f"IP address changed during verification for {username}.")

            profile_data.status = "verified"
            logger.success(f"Profile {username} successfully created and verified.")
        else:
            raise Exception("Could not find or use verification link.")

    except Exception as e:
        logger.error(f"An error occurred during profile creation for {username}: {e}")
        profile_data.status = "error"
        profile_data.error_message = str(e)
    finally:
        # 6. Log Profile and Clean Up
        save_profile_to_json(profile_data)
        await browser.close()
        adspower_api.stop_browser(user_id=adspower_id)
        logger.info(f"Finished processing for profile {username}.")


def run(
    emails_csv: Path = typer.Option(..., "--emails", help="Path to the CSV file with emails."),
    proxies_json: Path = typer.Option(..., "--proxies", help="Path to the JSON file with proxies."),
    max_accounts: int = typer.Option(10, "--max-accounts", help="Maximum number of accounts to create."),
    delay: int = typer.Option(5, "--delay", help="Delay in seconds between account creations."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate the process without creating accounts."),
) -> None:
    """
    Main entry point to start the profile creation process.
    This function is now a CLI command managed by Typer.
    """
    logger.info("Starting Reddit Profile Creator via CLI.")
    
    if not emails_csv.exists() or not proxies_json.exists():
        logger.error("Emails CSV or Proxies JSON file not found.")
        raise typer.Exit(code=1)

    # Config is now loaded automatically from .env into the global settings object
    if not settings.caps_key or not settings.adspower_group_id:
        logger.error(
            "Required settings (CAPS_KEY, ADSPOWER_GROUP_ID) not found in .env file."
        )
        raise typer.Exit(code=1)

    # Initialize APIs with the new centralized settings
    adspower = AdsPowerAPI() # No need to pass URL if using default
    captcha = CaptchaSolver()
    gmail = GmailAPI()

    # Read input files
    with open(emails_csv, "r") as f:
        emails = [line.strip() for line in f if line.strip()]
    with open(proxies_json, "r") as f:
        proxies = json.load(f)
    
    if not emails or not proxies:
        logger.error("Emails or proxies list is empty.")
        raise typer.Exit(code=1)

    # Limit accounts to create
    emails_to_process = emails[:min(len(emails), max_accounts)]
    
    logger.info(f"Preparing to create {len(emails_to_process)} accounts.")

    if dry_run:
        logger.info("--- DRY RUN ENABLED ---")
        logger.info("Would process the following emails:")
        for email in emails_to_process:
            logger.info(f"- {email}")
        logger.info("-----------------------")
        raise typer.Exit()

    async def main():
        tasks = []
        for i, email in enumerate(emails_to_process):
            # Rotate through proxies
            proxy = proxies[i % len(proxies)]
            
            task = create_single_profile(
                adspower_api=adspower,
                captcha_solver=captcha,
                gmail_api=gmail,
                email_address=email,
                proxy_config=proxy,
            )
            tasks.append(task)
            
            # Add delay between starting tasks
            if i < len(emails_to_process) - 1:
                await asyncio.sleep(delay)
        
        await asyncio.gather(*tasks)

    asyncio.run(main())
    logger.info("Reddit Profile Creator has finished.")


if __name__ == "__main__":
    typer.run(run) 