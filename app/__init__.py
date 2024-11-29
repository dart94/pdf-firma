from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from decouple import config
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configuraciones de la aplicación
    app.config["UPLOAD_FOLDER"] = "uploads"
    app.config["SIGNED_FOLDER"] = "signed"
    app.config["SQLALCHEMY_DATABASE_URI"] = config("DATABASE_URL")
    app.config["SECRET_KEY"] = config("SECRET_KEY")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar blueprints
    from .routes import main
    app.register_blueprint(main)

    return app
