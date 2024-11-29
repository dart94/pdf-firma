from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone

db = SQLAlchemy()

class SignatureRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    is_signed = db.Column(db.Boolean, default=False)
    signed_pdf = db.Column(db.LargeBinary, nullable=True)
    
    def is_expired(self):
        # Convertir expires_at a datetime con zona horaria UTC si no lo tiene
        if self.expires_at.tzinfo is None:
            expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at_aware = self.expires_at
        
        return datetime.now(timezone.utc) > expires_at_aware
