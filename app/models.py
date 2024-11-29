from . import db
from datetime import datetime, timedelta, timezone

class SignatureRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    is_signed = db.Column(db.Boolean, default=False)
    signed_pdf = db.Column(db.LargeBinary, nullable=True)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at
