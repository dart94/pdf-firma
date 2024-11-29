from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

class SignatureRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow_with_timezone)
    is_signed = db.Column(db.Boolean, default=False)
    signed_pdf = db.Column(db.LargeBinary, nullable=True)

    @staticmethod
    def utcnow_with_timezone():
        return datetime.now
