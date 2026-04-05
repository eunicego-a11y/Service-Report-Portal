import os
import json
import base64
import traceback

import requests
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session,
)
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import oauth
from ..models import User
from ..user_store import read_users, write_users

auth_bp = Blueprint("auth", __name__)

ALLOWED_DOMAIN = "mcbtsi.com"


def _is_allowed_email(email: str) -> bool:
    """Return True only for @mcbtsi.com addresses."""
    return email.strip().lower().endswith(f"@{ALLOWED_DOMAIN}")


# ── Traditional login / signup ────────────────────────────────────────────────

@auth_bp.route("/signup")
def signup():
    """Signup is handled via OAuth — redirect straight to login."""
    return redirect(url_for("auth.login"))


@auth_bp.route("/login")
def login():
    google_enabled = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
    return render_template("auth/login.html", google_enabled=google_enabled)


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# ── Monday.com OAuth ──────────────────────────────────────────────────────────

@auth_bp.route("/auth/monday")
def monday_login():
    monday = oauth.create_client("monday")
    if not monday:
        flash("Monday.com login is not configured.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.monday_callback", _external=True)
    try:
        return monday.authorize_redirect(redirect_uri)
    except Exception as e:
        print(f"[OAUTH] authorize_redirect error: {e}")
        flash(f"Authentication error: {e}", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/auth/monday/callback")
def monday_callback():
    try:
        error = request.args.get("error")
        if error:
            flash(f"Monday.com auth failed: {request.args.get('error_description', error)}", "error")
            return redirect(url_for("auth.login"))

        code = request.args.get("code")
        if not code:
            flash("No authorization code received.", "error")
            return redirect(url_for("auth.login"))

        token_data = {
            "client_id": os.getenv("MONDAY_OAUTH_CLIENT_ID"),
            "client_secret": os.getenv("MONDAY_OAUTH_CLIENT_SECRET"),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_for("auth.monday_callback", _external=True),
        }
        token_response = requests.post(
            "https://auth.monday.com/oauth2/token", data=token_data, timeout=10
        )
        token_response.raise_for_status()
        token = token_response.json()

        access_token = token.get("access_token")
        if not access_token:
            flash("Failed to get access token from Monday.com.", "error")
            return redirect(url_for("auth.login"))

        # Decode JWT to extract user ID without an extra API call
        parts = access_token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        claims = json.loads(base64.urlsafe_b64decode(payload))

        monday_user_id = claims.get("uid")
        monday_account_id = claims.get("actid")
        if not monday_user_id:
            flash("Failed to extract user info from Monday.com token.", "error")
            return redirect(url_for("auth.login"))

        # Fetch this user's email from Monday API and validate domain
        try:
            me_resp = requests.post(
                "https://api.monday.com/v2",
                json={"query": "{ me { email name } }"},
                headers={"Authorization": access_token, "Content-Type": "application/json"},
                timeout=10,
            )
            me_data = me_resp.json().get("data", {}).get("me") or {}
            monday_email = (me_data.get("email") or "").strip().lower()
            monday_name = me_data.get("name") or ""
        except Exception:
            monday_email = ""
            monday_name = ""

        if monday_email and not _is_allowed_email(monday_email):
            flash(f"Only @{ALLOWED_DOMAIN} Monday.com accounts may sign in.", "error")
            return redirect(url_for("auth.login"))

        username = monday_email or f"monday_{monday_user_id}"
        name = monday_name or f"Monday User {monday_user_id}"

        users = read_users()
        user_db = next((u for u in users if u.get("username") == username), None)
        if not user_db:
            users.append({
                "username": username, "email": username, "name": name,
                "monday_id": monday_user_id, "monday_account_id": monday_account_id,
                "provider": "monday", "password": None,
            })
        else:
            user_db.update({"monday_id": monday_user_id, "monday_account_id": monday_account_id, "provider": "monday"})
        write_users(users)

        session["monday_token"] = access_token
        session["monday_user_id"] = monday_user_id
        session["monday_account_id"] = monday_account_id
        session.permanent = True

        login_user(User(username, name), remember=True)
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        print(f"[OAUTH] Monday callback error: {e}")
        print(traceback.format_exc())
        flash("Authentication failed. Check server logs for details.", "error")
        return redirect(url_for("auth.login"))


# ── Google OAuth ──────────────────────────────────────────────────────────────

@auth_bp.route("/auth/google")
def google_login():
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        flash("Google sign-in is not configured yet. Please contact your administrator.", "error")
        return redirect(url_for("auth.login"))
    google = oauth.create_client("google")
    if not google:
        flash("Google sign-in is not available. Please contact your administrator.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback():
    try:
        google = oauth.create_client("google")
        token = google.authorize_access_token()
        userinfo = token.get("userinfo") or google.userinfo(token=token)

        email = (userinfo.get("email") or "").strip().lower()
        name = userinfo.get("name") or email
        google_sub = userinfo.get("sub")

        if not email:
            flash("Could not retrieve email from Google.", "error")
            return redirect(url_for("auth.login"))
        if not userinfo.get("email_verified", True):
            flash("Your Google account email is not verified.", "error")
            return redirect(url_for("auth.login"))
        if not _is_allowed_email(email):
            flash(f"Only @{ALLOWED_DOMAIN} Google accounts may sign in.", "error")
            return redirect(url_for("auth.login"))

        users = read_users()
        user_data = next((u for u in users if u.get("email") == email or u.get("username") == email), None)
        if not user_data:
            users.append({
                "username": email, "email": email, "name": name,
                "google_sub": google_sub, "provider": "google", "password": None,
            })
        else:
            user_data["google_sub"] = google_sub
            user_data["provider"] = "google"
            if not user_data.get("name"):
                user_data["name"] = name
        write_users(users)

        session.permanent = True
        login_user(User(email, name), remember=True)
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("main.index"))

    except Exception as e:
        print(f"[GOOGLE] Callback error: {e}")
        print(traceback.format_exc())
        flash("Google authentication failed. Please try again.", "error")
        return redirect(url_for("auth.login"))
