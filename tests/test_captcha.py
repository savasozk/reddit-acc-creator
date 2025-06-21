import pytest
import respx
from httpx import Response

from src.captcha import CaptchaSolver
from src.config import settings

# Mock API keys for testing
settings.caps_key = "test_caps_key"
settings.captcha_2_key = "test_2captcha_key"
settings.captcha_retries = 2 # Lower retries for faster tests


@pytest.mark.asyncio
@respx.mock
async def test_solve_recaptcha_v2_capsolver_success():
    """Test successful CAPTCHA solve with CapSolver."""
    # Mock CapSolver's create task and get result endpoints
    respx.post("https://api.capsolver.com/createTask").mock(
        return_value=Response(200, json={"errorId": 0, "taskId": "123"})
    )
    respx.post("https://api.capsolver.com/getTaskResult").mock(
        return_value=Response(200, json={
            "errorId": 0,
            "status": "ready",
            "solution": {"gRecaptchaResponse": "solved_token"},
        })
    )
    
    solver = CaptchaSolver()
    solution = await solver.solve_recaptcha_v2("http://example.com", "sitekey123")
    
    assert solution == "solved_token"


@pytest.mark.asyncio
@respx.mock
async def test_solve_recaptcha_v2_fallback_to_2captcha():
    """Test fallback to 2Captcha when CapSolver fails."""
    # Mock CapSolver to consistently fail
    respx.post("https://api.capsolver.com/createTask").mock(
        return_value=Response(200, json={"errorId": 1, "errorCode": "ERROR_KEY_DOES_NOT_EXIST"})
    )
    
    # Mock 2Captcha
    respx.get(url__regex=r"https://2captcha.com/in.php.*").mock(
        return_value=Response(200, text="OK|12345")
    )
    respx.get(url__regex=r"https://2captcha.com/res.php.*").mock(
        return_value=Response(200, text="OK|solved_token_2captcha")
    )

    solver = CaptchaSolver()
    solution = await solver.solve_recaptcha_v2("http://example.com", "sitekey123")

    assert solution == "solved_token_2captcha"


@pytest.mark.asyncio
@respx.mock
async def test_solve_recaptcha_v2_all_fail():
    """Test when both CapSolver and 2Captcha fail."""
    # Mock CapSolver to fail
    respx.post("https://api.capsolver.com/createTask").mock(
        return_value=Response(500)
    )
    # Mock 2Captcha to fail
    respx.get(url__regex=r"https://2captcha.com/in.php.*").mock(
        return_value=Response(200, text="ERROR_WRONG_USER_KEY")
    )

    solver = CaptchaSolver()
    solution = await solver.solve_recaptcha_v2("http://example.com", "sitekey123")

    assert solution is None 