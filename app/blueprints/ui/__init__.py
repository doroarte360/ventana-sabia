from flask import Blueprint

bp = Blueprint("ui", __name__)
from . import routes  # noqa
