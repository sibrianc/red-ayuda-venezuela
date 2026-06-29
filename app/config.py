import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    APP_NAME = os.getenv("APP_NAME", "Red de Ayuda Venezuela")
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.getenv(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'instance' / 'red_ayuda_dev.sqlite3'}",
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600
    REPORTS_PER_PAGE = 20
    JSON_SORT_KEYS = False
    MAP_TILE_URL = os.getenv(
        "MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    )
    # Operación autónoma: publica reportes limpios sin revisión humana (los que no
    # pasan la verificación automática quedan en cola). Pon AUTO_PUBLISH=false para
    # exigir aprobación manual cuando haya personas revisando.
    AUTO_PUBLISH = os.getenv("AUTO_PUBLISH", "true").lower() in {"1", "true", "yes", "on"}
    # Reenvío automático a instituciones (solo proyección pública, sin datos privados).
    INSTITUTION_FORWARD_ENABLED = os.getenv("INSTITUTION_FORWARD_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    INSTITUTION_WEBHOOK_URL = os.getenv("INSTITUTION_WEBHOOK_URL", "").strip() or None


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        if not os.getenv("SECRET_KEY") or cls.SECRET_KEY == "development-only-change-me":
            raise RuntimeError("SECRET_KEY debe configurarse en producción.")
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL debe configurarse en producción.")


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SERVER_NAME = "localhost"


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
