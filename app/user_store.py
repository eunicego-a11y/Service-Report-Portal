import os
import json
from datetime import datetime, timezone

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "users.json")
SUBMISSIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "submissions.json")


def read_users() -> list:
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def write_users(users: list) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


# ── Submission log ────────────────────────────────────────────────────────────

def log_submission(username: str, item_name: str, item_id: str) -> None:
    """Append a submission record to submissions.json."""
    try:
        entries = []
        if os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, "r") as f:
                try:
                    entries = json.load(f)
                except (json.JSONDecodeError, ValueError):
                    entries = []

        entries.append({
            "username": username,
            "name": item_name,
            "item_id": item_id,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

        # Keep last 500 entries total
        if len(entries) > 500:
            entries = entries[-500:]

        with open(SUBMISSIONS_FILE, "w") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        print(f"[log_submission] Error: {e}")


def get_user_submissions(username: str, limit: int = 20) -> list:
    """Return the most recent submissions for a given username."""
    if not os.path.exists(SUBMISSIONS_FILE):
        return []
    try:
        with open(SUBMISSIONS_FILE, "r") as f:
            entries = json.load(f)
        user_entries = [e for e in entries if e.get("username") == username]
        return list(reversed(user_entries[-limit:]))
    except (json.JSONDecodeError, ValueError, OSError):
        return []
