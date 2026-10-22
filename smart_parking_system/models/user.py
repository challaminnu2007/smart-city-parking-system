from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db

class User(db.Model):
    """User model representing customers and administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mobile_number = db.Column(db.String(20), nullable=False, index=True)
    vehicle_number = db.Column(db.String(25), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='USER')  # 'USER' or 'ADMIN'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    bookings = db.relationship('Booking', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='user', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')

    def set_password(self, password: str):
        """Securely hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify given password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        """Check if user has administrator privileges."""
        return self.role == 'ADMIN'

    def to_dict(self, include_sensitive: bool = False):
        """Serialize user object to dictionary."""
        data = {
            'id': self.id,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'mobile_number': self.mobile_number,
            'vehicle_number': self.vehicle_number,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        return data

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'
