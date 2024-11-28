import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde un archivo .env

class Config:
    # Configuración general
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///local.db"  # Fallback a SQLite en desarrollo
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "uploads"
    SIGNED_FOLDER = "signed"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB como límite de subida de archivo