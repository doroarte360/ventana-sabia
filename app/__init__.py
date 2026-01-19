import logging

from flask import Flask, jsonify, request, abort, session
from werkzeug.local import LocalProxy

from .config import get_config
from .extensions import db, migrate
from .security.security_events import record_security_event



# -------------------------------------------------
# Fix LocalProxy(request) para stacks complejos
# -------------------------------------------------
def _install_request_proxy_fix():
    import flask.globals as g
    import flask.app as flask_app
    import flask.ctx as flask_ctx

    fixed_request = LocalProxy(lambda: g._cv_request.get(), "request")

    g.request = fixed_request
    flask_app.request = fixed_request
    flask_ctx.request = fixed_request


# -------------------------------------------------
# App factory
# -------------------------------------------------
def create_app(config_overrides: dict | None = None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config())

    if config_overrides:
        app.config.update(config_overrides)

    _install_request_proxy_fix()

    logging.basicConfig(level=logging.INFO)
    app.logger.info("Ventana Sabia - init app")

    # -----------------------------
    # Extensions
    # -----------------------------
    db.init_app(app)

    from . import models  # noqa: F401
    migrate.init_app(app, db)

    # -----------------------------
    # Blueprints
    # -----------------------------
    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.books.routes import bp as books_bp
    from .blueprints.admin.routes import bp as admin_bp
    from .blueprints.book_requests.routes import bp as book_requests_bp
    from .blueprints.ui import bp as ui_bp
    from .blueprints.admin_api import bp as admin_api_bp

    app.register_blueprint(admin_api_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(book_requests_bp)
    app.register_blueprint(admin_bp)

    # -----------------------------
    # RBAC rules
    # -----------------------------
    from .security.access import Rule, is_public_endpoint, check_access

    ACCESS_RULES = [
        Rule(blueprint="admin", methods={"*"}, roles={"admin"}),

        Rule(blueprint="books", methods={"GET", "HEAD"}, roles={"reader", "admin"}),
        Rule(blueprint="books", methods={"POST", "PATCH"}, roles={"reader", "admin"}),
        Rule(blueprint="books", methods={"DELETE"}, roles={"admin"}),

        Rule(blueprint="book_requests", methods={"*"}, roles={"reader", "admin"}),
    ]

    # -----------------------------
    # Error handlers (JSON)
    # -----------------------------
    @app.errorhandler(401)
    def err_401(e):
        return jsonify(error="unauthorized"), 401

    @app.errorhandler(403)
    def err_403(e):
        return jsonify(error="forbidden"), 403

    @app.errorhandler(404)
    def err_404(e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(429)
    def err_429(e):
        return jsonify(error="too_many_requests"), 429

    # -----------------------------
    # Global RBAC + rate limit
    # -----------------------------
    @app.before_request
    def enforce_global_access_min():
        if request.endpoint is None:
            return None

        endpoint = request.endpoint
        bp = request.blueprint

        # Preflight
        if request.method == "OPTIONS":
            return None

        # Públicos simples
        if endpoint in {"static", "health", "routes"}:
            return None

        # Rate limit SOLO auth.*
        if (not app.config.get("TESTING")) and endpoint.startswith("auth."):
            from .security.rate_limit import hit

            xff = request.headers.get("X-Forwarded-For")
            ip = (xff.split(",")[0].strip() if xff else request.remote_addr) or "unknown"

            if endpoint == "auth.login":
                limit, window = 10, 60
            elif endpoint == "auth.register":
                limit, window = 6, 60
            else:
                limit, window = 20, 60

            key = f"{ip}:{endpoint}"
            if not hit(key, limit=limit, window_sec=window):
                record_security_event(
                    event_type="rate_limited",
                    status_code=429,
                    req=request,
                    user=None,
                    details=f"limit={limit} window={window}",
                )
                abort(429)

            return None  # auth es público

        # UI pública
        if bp == "ui" or endpoint.startswith("ui."):
            return None

        # Otros públicos declarados
        if is_public_endpoint(endpoint):
            return None

        # Requiere login
        user_id = session.get("user_id")
        if not user_id:
            record_security_event(
                event_type="deny_unauthorized",
                status_code=401,
                req=request,
                user=None,
                details="missing session user_id",
            )
            abort(401)

        from .models import User
        user = db.session.get(User, user_id)

        # Usuario bloqueado
        if user and getattr(user, "is_blocked", False):
            record_security_event(
                event_type="deny_blocked",
                status_code=403,
                req=request,
                user=user,
                details="user blocked",
            )
            abort(403)

        # RBAC fino
        if not check_access(user, request, ACCESS_RULES):
            record_security_event(
                event_type="deny_forbidden",
                status_code=403,
                req=request,
                user=user,
                details=f"bp={request.blueprint}",
            )
            abort(403)

        return None

    # -----------------------------
    # Health / debug
    # -----------------------------
    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        return "Ventana Sabia ✅"

    @app.get("/routes")
    def routes():
        return jsonify(sorted([str(r) for r in app.url_map.iter_rules()]))

    # 🔴 ESTE RETURN ES CLAVE
    return app
