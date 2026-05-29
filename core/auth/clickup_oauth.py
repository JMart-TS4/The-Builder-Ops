import json
import secrets
import urllib.parse
import requests
from pathlib import Path

from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

TOKEN_PATH   = "credentials/clickup_token_login.json"
CLICKUP_BASE = "https://api.clickup.com/api/v2"


def get_auth_url() -> str:
    """Build and return the ClickUp OAuth authorization URL with a state prefix."""
    state = "clickup_" + secrets.token_urlsafe(8)
    params = urllib.parse.urlencode({
        "client_id":    settings.clickup_client_id,
        "redirect_uri": settings.clickup_redirect_uri,
        "state":        state,
    })
    return f"https://app.clickup.com/api?{params}"


def exchange_code(code: str) -> dict:
    """Exchange OAuth code for an access token, save it, return user info."""
    resp = requests.post(
        f"{CLICKUP_BASE}/oauth/token",
        params={
            "client_id":     settings.clickup_client_id,
            "client_secret": settings.clickup_client_secret,
            "code":          code,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise ValueError("ClickUp no devolvió access_token")

    Path("credentials").mkdir(exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump({"access_token": token}, f)

    user_resp = requests.get(
        f"{CLICKUP_BASE}/user",
        headers={"Authorization": token},
        timeout=10,
    )
    user_data = user_resp.json().get("user", {}) if user_resp.ok else {}

    logger.info(f"ClickUp OAuth completado | usuario={user_data.get('email', '?')}")
    return {"access_token": token, "user": user_data}


def get_saved_token() -> str | None:
    """Return the saved ClickUp access token, or None."""
    if not Path(TOKEN_PATH).exists():
        return None
    try:
        with open(TOKEN_PATH) as f:
            return json.load(f).get("access_token")
    except Exception:
        return None


def is_authenticated() -> bool:
    """True if a ClickUp token is saved on disk."""
    return bool(get_saved_token())
