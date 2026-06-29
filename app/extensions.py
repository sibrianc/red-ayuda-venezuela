from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
# Límite de tasa por IP. Storage en memoria por defecto (apto para un proceso/local);
# en producción multi-worker conviene Redis vía RATELIMIT_STORAGE_URI.
limiter = Limiter(key_func=get_remote_address)

login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesión para acceder al área administrativa."
login_manager.login_message_category = "warning"
