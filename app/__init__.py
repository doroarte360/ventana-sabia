import logging

from flask import Flask, jsonify, request, abort, session
from werkzeug.local import LocalProxy

from .config import get_config
from .extensions import db, migrate
from .security.security_events import record_security_event


def _install_request_proxy_fix():
    """
    Fix global `request` LocalProxy. In this stack, _cv_request already holds the Request object.
    """
    import flask.globals as g
    import flask.app as flask_app
    import flask.ctx as flask_ctx

    fixed_request = LocalProxy(lambda: g._cv_request.get(), "request")

    g.request = fixed_request
    flask_app.request = fixed_request
    flask_ctx.request = fixed_request


def create_app(config_overrides: dict | None = None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config())

    # ✅ Apply overrides BEFORE db.init_app so SQLAlchemy uses test DB
    if config_overrides:
        app.config.update(config_overrides)

    # ✅ Install fix BEFORE anything that might touch request.blueprints
    _install_request_proxy_fix()

    logging.basicConfig(level=logging.INFO)
    app.logger.info("Ventana Sabia - init app")

    db.init_app(app)

    # load models so Alembic detects tables / metadata exists
    from . import models  # noqa: F401

    migrate.init_app(app, db)

    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.books.routes import bp as books_bp
    from .blueprints.admin.routes import bp as admin_bp
    from .blueprints.book_requests.routes import bp as book_requests_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(book_requests_bp)
    app.register_blueprint(admin_bp)

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
    # RBAC / Enforcement global + rate limit (auth)
    # -----------------------------
    @app.before_request
    def enforce_global_access_min():
        # 0) endpoint None suele ser 404 / rutas no resueltas
        if request.endpoint is None:
            return

        # 1) permitir preflight CORS
        if request.method == "OPTIONS":
            return

        # 2) permitir estáticos
        if request.endpoint == "static":
            return

        # 3) rate limit SOLO para auth.* y NO en tests
        #    OJO: auth.* es público, por eso va ANTES del return de is_public_endpoint
        if (not app.config.get("TESTING")) and request.endpoint.startswith("auth."):
            from .security.rate_limit import hit

            xff = request.headers.get("X-Forwarded-For")
            ip = (xff.split(",")[0].strip() if xff else request.remote_addr) or "unknown"

            if request.endpoint == "auth.login":
                limit, window_sec = 10, 60
            elif request.endpoint == "auth.register":
                limit, window_sec = 6, 60
            else:
                limit, window_sec = 20, 60

            key = f"{ip}:{request.endpoint}"
            if not hit(key, limit=limit, window_sec=window_sec):
                app.logger.info(
                    "RATE LIMIT 429: ip=%s endpoint=%s limit=%s window=%s",
                    ip, request.endpoint, limit, window_sec
                )
                record_security_event(
                    event_type="rate_limited",
                    status_code=429,
                    req=request,
                    user=None,
                    details=f"limit={limit} window={window_sec} key={key}",
                )
                abort(429)

        # 4) públicos: auth.* (pese a rate limit), health/index/routes, etc.
        if is_public_endpoint(request.endpoint):
            return

        # 5) a partir de aquí: requiere login
        user_id = session.get("user_id")
        if not user_id:
            app.logger.info(
                "RBAC DENY 401: no session user_id | endpoint=%s method=%s path=%s",
                request.endpoint, request.method, request.path,
            )
            record_security_event(
                event_type="deny_unauthorized",
                status_code=401,
                req=request,
                user=None,
                details="missing session user_id",
            )
            abort(401)

        # 6) cargar usuario
        from .models import User
        user = db.session.get(User, user_id)

        # 7) bloqueo global
        if user and (getattr(user, "is_blocked", False) is True or getattr(user, "status", None) == "blocked"):
            app.logger.info(
                "RBAC DENY 403: blocked user_id=%s role=%s | endpoint=%s method=%s path=%s",
                user_id, getattr(user, "role", None),
                request.endpoint, request.method, request.path,
            )
            record_security_event(
                event_type="deny_blocked",
                status_code=403,
                req=request,
                user=user,
                details="user blocked",
            )
            abort(403)

        # 8) RBAC fino por reglas
        if not check_access(user, request, ACCESS_RULES):
            app.logger.info(
                "RBAC DENY 403: forbidden user_id=%s role=%s bp=%s | endpoint=%s method=%s path=%s",
                user_id, getattr(user, "role", None), request.blueprint,
                request.endpoint, request.method, request.path,
            )
            record_security_event(
                event_type="deny_forbidden",
                status_code=403,
                req=request,
                user=user,
                details=f"bp={request.blueprint}",
            )
            abort(403)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        return "Ventana Sabia ✅"

    @app.get("/routes")
    def routes():
        return jsonify(sorted([str(r) for r in app.url_map.iter_rules()]))

    return app
