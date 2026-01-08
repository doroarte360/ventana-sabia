from flask import Blueprint, jsonify

bp = Blueprint("admin", __name__, url_prefix="/admin")

@bp.get("/ping")
def ping_admin():
    return jsonify(ok=True, area="admin")
