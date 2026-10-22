from datetime import datetime, timezone
from database.db import db

class ParkingSlot(db.Model):
    """Parking slot model representing physical parking spaces."""
    __tablename__ = 'parking_slots'

    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    zone = db.Column(db.String(60), nullable=False, index=True)
    floor = db.Column(db.String(30), default='Ground', nullable=False)
    slot_type = db.Column(db.String(40), default='Standard', nullable=False)  # Standard, Compact, SUV, EV Charging, Accessible
    status = db.Column(db.String(20), default='AVAILABLE', nullable=False, index=True)  # AVAILABLE, RESERVED, OCCUPIED, MAINTENANCE
    hourly_rate = db.Column(db.Float, default=30.0, nullable=False)
    is_sample = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    # Relationships
    bookings = db.relationship('Booking', back_populates='slot', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'slot_number': self.slot_number,
            'zone': self.zone,
            'floor': self.floor,
            'slot_type': self.slot_type,
            'status': self.status,
            'hourly_rate': self.hourly_rate,
            'is_sample': self.is_sample,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<ParkingSlot {self.slot_number} [{self.status}]>'
