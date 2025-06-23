import json
import time
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from src.config import settings


class AdsPowerAPI:
    """A wrapper for the AdsPower Local API."""

    def __init__(self, api_url: Optional[str] = None):
        """Initializes the AdsPowerAPI client."""
        self.base_url = api_url or settings.adspower_api_url
        self._check_api_status()

    def _check_api_status(self) -> None:
        """Checks if the AdsPower application is running."""
        try:
            requests.get(f"{self.base_url}/status", timeout=5)
            logger.info("AdsPower Local API is running.")
        except requests.exceptions.ConnectionError as e:
            logger.error(
                "AdsPower Local API is not accessible. "
                "Please ensure AdsPower is running and the Local API is enabled."
            )
            raise ConnectionError(
                "Could not connect to AdsPower Local API."
            ) from e

    def create_profile(
        self,
        name: str,
        group_id: str,
        proxy_config: Dict[str, Any],
        fingerprint_config: Dict[str, Any],
    ) -> Optional[str]:
        """
        Creates a new browser profile in AdsPower.

        Args:
            name: The desired name for the profile.
            group_id: The ID of the group to add the profile to.
            proxy_config: Dictionary containing proxy settings.
            fingerprint_config: Dictionary containing fingerprint settings.

        Returns:
            The user_id of the newly created profile, or None on failure.
        """
        payload = {
            "name": name,
            "group_id": group_id,
            "user_proxy_config": proxy_config,
            "fingerprint_config": fingerprint_config,
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/user/create", json=payload, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and data.get("data", {}).get("id"):
                profile_id = data["data"]["id"]
                logger.success(f"Successfully created AdsPower profile '{name}' with ID: {profile_id}")
                return profile_id
            else:
                logger.error(f"Failed to create profile. Response: {data}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while creating profile: {e}")
            return None

    def list_profiles(self, group_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists all profiles, optionally filtered by group_id.

        Args:
            group_id: The group ID to filter profiles by.

        Returns:
            A list of profile dictionaries.
        """
        params = {"group_id": group_id} if group_id else {}
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/user/list", params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and "list" in data.get("data", {}):
                profile_list = data["data"]["list"]
                logger.info(f"Successfully retrieved {len(profile_list)} profiles.")
                return profile_list
            else:
                logger.error(f"Failed to list profiles. Response: {data}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while listing profiles: {e}")
            return []

    def start_browser(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Starts the browser for a given profile ID.

        Args:
            user_id: The user_id of the profile to launch.

        Returns:
            A dictionary containing webdriver path and debug ws endpoint, or None.
        """
        # The API expects list-like arguments to be JSON strings.
        launch_args_json = json.dumps(["--window-size=800,600"])
        params = {"user_id": user_id, "launch_args": launch_args_json}
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/browser/start", params=params, timeout=60
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0 and data.get("data"):
                logger.info(f"Browser for profile ID {user_id} started successfully.")
                return data["data"]
            else:
                logger.error(f"Failed to start browser. Response: {data}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while starting browser: {e}")
            return None

    def stop_browser(self, user_id: str) -> bool:
        """
        Stops the browser for a given profile ID.

        Args:
            user_id: The user_id of the profile to stop.

        Returns:
            True if the browser was stopped successfully, False otherwise.
        """
        params = {"user_id": user_id}
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/browser/stop", params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            if data.get("code") == 0:
                logger.info(f"Browser for profile ID {user_id} stopped successfully.")
                return True
            else:
                logger.error(f"Failed to stop browser. Response: {data}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while stopping browser: {e}")
            return False 