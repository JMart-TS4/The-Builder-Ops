import json
import os
from datetime import datetime, timezone

_STATE_DIR = "credentials"


def get_last_sync(user_id: str) -> datetime | None:
    path = os.path.join(_STATE_DIR, f"sync_state_{user_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    ts = data.get("last_sync")
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def save_last_sync(user_id: str, ts: datetime) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    path = os.path.join(_STATE_DIR, f"sync_state_{user_id}.json")
    with open(path, "w") as f:
        json.dump({"last_sync": ts.strftime("%Y-%m-%dT%H:%M:%SZ")}, f)
