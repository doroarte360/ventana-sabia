import os
from dataclasses import dataclass

def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _default_sqlite_uri() -> str:
    # app/ -> proyecto/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    instance_dir = os.path.join(project_root, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    db_path = os.path.join(instance_dir, "ventana_sabia.db")
    return "sqlite:///" + db_path

@dataclass(frozen=True)
class BaseConfig:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", _default_sqlite_uri())
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_COOKIE_SECURE: bool = _bool(os.getenv("SESSION_COOKIE_SECURE"), default=False)

class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True

class ProductionConfig(BaseConfig):
    DEBUG: bool = False

def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
