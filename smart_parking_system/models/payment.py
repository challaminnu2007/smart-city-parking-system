from datetime import datetime, timezone
from database.db import db

class Payment(db.Model):
    """Payment transaction model recording all payment attempts."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    payment_reference = db.Column(db.String(80), unique=True, nullable=False, index=True)
    order_reference = db.Column(db.String(80), nullable=True, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR', nullable=False)
    
    payment_method = db.Column(db.String(40), default='DEV_SIMULATOR', nullable=False)
    payment_gateway = db.Column(db.String(40), default='LOCAL_DEV_SIMULATOR', nullable=False)
    
    # Statuses: SUCCESS, FAILED, PENDING, REFUNDED
    status = db.Column(db.String(25), default='PENDING', nullable=False, index=True)
    gateway_signature = db.Column(db.String(255), nullable=True)
    is_simulated = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    booking = db.relationship('Booking', back_populates='payment')
    user = db.relationship('User', back_populates='payments')

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'booking_reference': self.booking.booking_reference if self.booking else None,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'payment_reference': self.payment_reference,
            'order_reference': self.order_reference,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_gateway': self.payment_gateway,
            'status': self.status,
            'is_simulated': self.is_simulated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Payment {self.payment_reference} [{self.status}] ₹{self.amount}>'
