import os
import traceback


def register_providers(oauth):
    """Register all OAuth providers. Called once during app factory init."""

    # ── Monday.com ──────────────────────────────────────────────────
    client_id = os.getenv("MONDAY_OAUTH_CLIENT_ID")
    client_secret = os.getenv("MONDAY_OAUTH_CLIENT_SECRET")
    print(f"[OAUTH] Monday.com — client_id set: {bool(client_id)}")
    try:
        oauth.register(
            name="monday",
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://auth.monday.com/oauth2/authorize",
            access_token_url="https://auth.monday.com/oauth2/token",
            userinfo_endpoint="https://api.monday.com/v2",
            client_kwargs={},
            token_auth_method="client_secret_post",
        )
        print("[OAUTH] Monday.com configured OK")
    except Exception as e:
        print(f"[OAUTH] Monday.com config error: {e}")
        print(traceback.format_exc())

    # ── Google ───────────────────────────────────────────────────────
    google_id = os.getenv("GOOGLE_CLIENT_ID")
    print(f"[OAUTH] Google — client_id set: {bool(google_id)}")
    try:
        oauth.register(
            name="google",
            client_id=google_id,
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
        print("[OAUTH] Google configured OK")
    except Exception as e:
        print(f"[OAUTH] Google config error: {e}")
