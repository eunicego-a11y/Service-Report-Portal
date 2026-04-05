import os
import traceback

from flask import Blueprint, request, jsonify
from flask_login import login_required

from .. import monday

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Signature key → Monday.com column ID
SIG_COLUMN_MAP = {
    "sig_tsp": os.getenv("COL_TSP_SIGNATURE"),
    "sig_customer": os.getenv("COL_CUSTOMER_SIGNATURE"),
    "sig_biomed": os.getenv("COL_BIOMED_SIGNATURE"),
    "sig_tsp_workwith": os.getenv("COL_TSP_WORKWITH_SIGNATURE"),
}

# Simple in-process cache so we don't hammer Monday's users API
_users_cache: list = []


@api_bp.route("/users")
@login_required
def get_users():
    """Return Monday.com workspace users for the people picker."""
    global _users_cache
    q = request.args.get("q", "").strip().lower()
    try:
        if not _users_cache:
            res = monday.graphql("{ users { id name email photo_thumb } }")
            raw = (res or {}).get("data", {}).get("users") or []
            _users_cache = [
                {
                    "id": u["id"],
                    "name": u.get("name") or u.get("email", ""),
                    "email": u.get("email", ""),
                    "photo": u.get("photo_thumb") or "",
                }
                for u in raw
            ]

        results = _users_cache
        if q:
            results = [u for u in results if q in u["name"].lower() or q in u["email"].lower()]

        return jsonify({
            "results": [
                {
                    "id": u["id"],
                    "text": u["name"],
                    "email": u["email"],
                    "photo": u["photo"],
                    "initials": "".join(p[0].upper() for p in u["name"].split()[:2]),
                }
                for u in results[:50]
            ]
        })
    except Exception as e:
        print(f"[USERS] Error: {e}")
        traceback.print_exc()
        return jsonify({"results": []})


@api_bp.route("/upload_signature", methods=["POST"])
@login_required
def upload_signature():
    """
    AJAX endpoint: Upload a signature PNG to a Monday.com item column.
    Expects multipart: file (PNG blob), item_id, sig_key.
    """
    try:
        item_id = request.form.get("item_id")
        sig_key = request.form.get("sig_key")
        file = request.files.get("file")

        if not item_id or not sig_key or not file:
            return jsonify({"success": False, "error": "Missing item_id, sig_key, or file"}), 400

        column_id = SIG_COLUMN_MAP.get(sig_key)
        if not column_id:
            return jsonify({"success": False, "error": f"Unknown sig_key: {sig_key}. Check .env column IDs."}), 400

        file_data = file.read()
        if len(file_data) < 100:
            return jsonify({"success": False, "error": "File too small — likely empty signature"}), 400

        filename = f"{sig_key}_{item_id}.png"
        success, result = monday.upload_file(item_id, column_id, file_data, filename)

        if success:
            return jsonify({"success": True, "file_id": result})
        return jsonify({"success": False, "error": result})

    except Exception as e:
        print(f"[API SIG] Error: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
