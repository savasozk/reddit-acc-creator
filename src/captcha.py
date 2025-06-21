import asyncio
from typing import Optional

from loguru import logger
from capsolver_python import RecaptchaV2Task
from twocaptcha import TwoCaptcha
from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless

from src.config import settings


class CaptchaSolver:
    """A service to solve reCAPTCHA challenges."""

    def __init__(self):
        """Initializes the CAPTCHA solver clients."""
        self.anticaptcha_client = (
            recaptchaV2Proxyless() if settings.anticaptcha_key else None
        )
        if self.anticaptcha_client:
            self.anticaptcha_client.set_key(settings.anticaptcha_key)

        self.capsolver_client = (
            RecaptchaV2Task(settings.caps_key) if settings.caps_key else None
        )
        self.twocaptcha_solver = (
            TwoCaptcha(settings.captcha_2_key) if settings.captcha_2_key else None
        )
        self.retries = settings.captcha_retries

    async def solve_recaptcha_v2(
        self, website_url: str, website_key: str
    ) -> Optional[str]:
        """
        Solves a reCAPTCHA v2 challenge, with a fallback mechanism.

        Args:
            website_url: The URL where the CAPTCHA is present.
            website_key: The site key of the reCAPTCHA challenge.

        Returns:
            The CAPTCHA solution token, or None if it cannot be solved.
        """
        # Primary: Anti-Captcha
        if self.anticaptcha_client:
            logger.info("Attempting to solve CAPTCHA with Anti-Captcha.")
            try:
                self.anticaptcha_client.set_website_url(website_url)
                self.anticaptcha_client.set_website_key(website_key)
                
                solution = await asyncio.to_thread(self.anticaptcha_client.solve_and_return_solution)

                if solution:
                    logger.success("Successfully solved CAPTCHA with Anti-Captcha.")
                    return solution
                else:
                    logger.error(f"Anti-Captcha failed. Error: {self.anticaptcha_client.error_code}")
                    
            except Exception as e:
                logger.error(f"An error occurred with Anti-Captcha: {e}")

        # Fallback 1: CapSolver
        if self.capsolver_client:
            for attempt in range(self.retries):
                logger.info(f"Attempt {attempt + 1}/{self.retries} to solve CAPTCHA with CapSolver.")
                try:
                    task = self.capsolver_client.create_task(
                        task_type="RecaptchaV2TaskProxyLess",
                        website_url=website_url,
                        website_key=website_key,
                    )
                    solution = await asyncio.to_thread(self.capsolver_client.join_task_result, task)
                    if solution and solution.get("status") == "ready":
                        token = solution["gRecaptchaResponse"]
                        logger.success("Successfully solved CAPTCHA with CapSolver.")
                        return token
                    else:
                        logger.warning(f"CapSolver attempt failed. Response: {solution}")

                except Exception as e:
                    logger.error(f"Error with CapSolver on attempt {attempt + 1}: {e}")

        # Fallback 2: 2Captcha
        if self.twocaptcha_solver:
            logger.info("Falling back to 2Captcha.")
            try:
                result = await asyncio.to_thread(
                    self.twocaptcha_solver.recaptcha,
                    sitekey=website_key,
                    url=website_url,
                )
                if result and "code" in result:
                    token = result["code"]
                    logger.success("Successfully solved CAPTCHA with 2Captcha.")
                    return token
                else:
                    logger.error(f"2Captcha failed. Response: {result}")
            except Exception as e:
                logger.error(f"An error occurred with 2Captcha: {e}")

        logger.error("All attempts to solve CAPTCHA have failed.")
        return None 