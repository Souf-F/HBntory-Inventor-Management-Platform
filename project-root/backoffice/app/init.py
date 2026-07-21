"""
HBntory — Flask application factory.

Wires the app, the config, and the shared SQLAlchemy instance together.
Souf will register the auth/stock/users blueprints here once they're ready
(see routes/auth.py, routes/stock.py, routes/users.py, routes/middleware.py).
"""

from flask import Flask

from app.config import Config
from app.models import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    # --- Blueprints (registered here once each teammate's routes exist) ---
    # from app.routes.auth import auth_bp
    # from app.routes.stock import stock_bp
    # from app.routes.users import users_bp
    # app.register_blueprint(auth_bp)
    # app.register_blueprint(stock_bp)
    # app.register_blueprint(users_bp)

    return app