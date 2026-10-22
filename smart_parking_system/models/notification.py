from datetime import datetime, timezone
from database.db import db

class Notification(db.Model):
    """Notification model tracking SMS messages sent or simulated."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='SET NULL'), nullable=True, index=True)
    
    mobile_number = db.Column(db.String(25), nullable=False)
    message = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(35), default='LOCAL_DEV_LOG', nullable=False)  # TWILIO, LOCAL_DEV_LOG
    provider_ref = db.Column(db.String(100), nullable=True)  # SID or UUID
    
    # Statuses: SENT, DELIVERED, FAILED, PENDING_CONFIG, DEV_SIMULATED
    status = db.Column(db.String(30), default='SENT', nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='notifications')
    booking = db.relationship('Booking', back_populates='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'booking_id': self.booking_id,
            'booking_reference': self.booking.booking_reference if self.booking else None,
            'mobile_number': self.mobile_number,
            'message': self.message,
            'provider': self.provider,
            'provider_ref': self.provider_ref,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Notification to {self.mobile_number} [{self.status}]>'
