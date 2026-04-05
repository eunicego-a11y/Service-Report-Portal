import os
from flask_login import UserMixin
from .extensions import login_manager
from .user_store import read_users


class User(UserMixin):
    def __init__(self, id: str, name: str = "User"):
        self.id = id
        self.name = name


@login_manager.user_loader
def load_user(user_id: str):
    users = read_users()
    user_data = next((u for u in users if u["username"] == user_id), None)
    if user_data:
        return User(user_data["username"], user_data.get("name", user_data["username"]))
    return None
