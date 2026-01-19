from flask import Blueprint

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")

from . import routes  # noqa: E402,F401
