from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configuración
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite:///default.db"  # Cambia esto si no estás usando SQLite
    )
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "default_secret_key")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicialización de extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registro de blueprints
    from app.routes import main_blueprint
    app.register_blueprint(main_blueprint)

    return app
