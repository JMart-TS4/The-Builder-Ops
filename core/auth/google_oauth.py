import json
import secrets
from pathlib import Path
import requests as _requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from config.settings import settings
from config.logging import get_logger

logger = get_logger(__name__)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
]
TOKEN_PATH   = "credentials/gdrive_token.json"
USER_PATH    = "credentials/google_user.json"


def _redirect_uri() -> str:
    return settings.google_redirect_uri


def get_auth_url() -> str:
    """Build and return the Google OAuth authorization URL with a state prefix.

    PKCE is disabled (autogenerate_code_verifier=False) so the code_challenge
    is not added to the auth URL. This lets us exchange the code in a fresh
    Flow instance after the Streamlit redirect, without needing to persist
    and restore the code_verifier across sessions.
    """
    state = "google_" + secrets.token_urlsafe(8)
    flow = Flow.from_client_secrets_file(
        settings.google_drive_credentials_path,
        scopes=SCOPES,
        redirect_uri=_redirect_uri(),
        autogenerate_code_verifier=False,
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
        include_granted_scopes="true",
    )
    return auth_url


def exchange_code(code: str) -> dict:
    """Exchange OAuth code for credentials, save token, return user info dict.

    Uses Flow.fetch_token() (not a raw requests.post) so the library handles
    redirect_uri, client_secret, and token parsing correctly.
    PKCE is off (autogenerate_code_verifier=False) matching get_auth_url().
    """
    flow = Flow.from_client_secrets_file(
        settings.google_drive_credentials_path,
        scopes=SCOPES,
        redirect_uri=_redirect_uri(),
        autogenerate_code_verifier=False,
    )
    flow.fetch_token(code=code, timeout=15)
    creds = flow.credentials

    Path("credentials").mkdir(exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    resp = _requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    resp.raise_for_status()
    user_info = resp.json()

    user = {
        "name":   user_info.get("name", ""),
        "email":  user_info.get("email", ""),
        "avatar": user_info.get("picture", ""),
    }

    with open(USER_PATH, "w") as f:
        json.dump(user, f)

    logger.info(f"Google OAuth completado | usuario={user['email']}")
    return user


def get_user_info() -> dict | None:
    """Return saved Google user info, or None if not available."""
    if not Path(USER_PATH).exists():
        return None
    try:
        with open(USER_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def is_authenticated() -> bool:
    """True if a valid Google token AND user profile are saved on disk."""
    if not Path(USER_PATH).exists() or not Path(TOKEN_PATH).exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH)
        if creds.valid:
            return True
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            return True
    except Exception:
        pass
    return False
