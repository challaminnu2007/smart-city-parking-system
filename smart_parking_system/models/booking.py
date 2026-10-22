from datetime import datetime, timezone
from database.db import db

class Booking(db.Model):
    """Booking model representing parking slot reservations."""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(35), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('parking_slots.id'), nullable=False, index=True)
    vehicle_number = db.Column(db.String(25), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)
    duration_hours = db.Column(db.Integer, nullable=False)
    hourly_rate = db.Column(db.Float, default=30.0, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Statuses: PENDING_PAYMENT, CONFIRMED, CHECKED_IN, COMPLETED, CANCELLED, EXPIRED
    status = db.Column(db.String(25), default='PENDING_PAYMENT', nullable=False, index=True)
    
    # QR verification token & base64 image representation
    qr_code_data = db.Column(db.Text, nullable=True)
    qr_code_image = db.Column(db.Text, nullable=True)
    
    checked_in_at = db.Column(db.DateTime, nullable=True)
    checked_out_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='bookings')
    slot = db.relationship('ParkingSlot', back_populates='bookings')
    payment = db.relationship('Payment', back_populates='booking', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='booking', lazy='dynamic', cascade='all, delete-orphan')

    def is_active(self) -> bool:
        """Check if booking is currently active or upcoming."""
        return self.status in ('CONFIRMED', 'CHECKED_IN')

    def to_dict(self):
        return {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'user_mobile': self.user.mobile_number if self.user else None,
            'slot_id': self.slot_id,
            'slot_number': self.slot.slot_number if self.slot else None,
            'slot_zone': self.slot.zone if self.slot else None,
            'slot_floor': self.slot.floor if self.slot else None,
            'slot_type': self.slot.slot_type if self.slot else None,
            'vehicle_number': self.vehicle_number,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_hours': self.duration_hours,
            'hourly_rate': self.hourly_rate,
            'total_amount': self.total_amount,
            'status': self.status,
            'qr_code_data': self.qr_code_data,
            'has_qr_code': bool(self.qr_code_image),
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None,
            'checked_out_at': self.checked_out_at.isoformat() if self.checked_out_at else None,
            'payment_status': self.payment.status if self.payment else 'UNPAID',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Booking {self.booking_reference} [{self.status}]>'
