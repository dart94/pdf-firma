import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    # Crear la aplicación Flask
    app = Flask(__name__)
    
    # Cargar configuración desde config.py
    app.config.from_object('config.Config')
    
    # Crear carpetas para subida de archivos si no existen
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["SIGNED_FOLDER"], exist_ok=True)
    
    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Registrar rutas
    from app.routes import main_blueprint
    app.register_blueprint(main_blueprint)
    
    return app
