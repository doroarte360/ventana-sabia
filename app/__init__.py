import logging
from flask import Flask, jsonify

from .config import get_config
from .extensions import db, migrate

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config())

    logging.basicConfig(level=logging.INFO)
    app.logger.info("Ventana Sabia - init app")

    db.init_app(app)
    from . import models  # carga modelos para que Alembic detecte tablas
    migrate.init_app(app, db)

    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.books.routes import bp as books_bp
    from .blueprints.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(admin_bp)

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
