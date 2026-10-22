import math
import uuid
from datetime import datetime, timezone, timedelta
from flask import current_app
from database.db import db
from models.booking import Booking
from models.parking_slot import ParkingSlot
from models.audit_log import AuditLog

def to_naive_utc(dt: datetime) -> datetime:
    """Normalize datetime object to timezone-naive UTC for consistent database storage and comparison."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

class BookingService:
    @classmethod
    def calculate_billable_hours(cls, start_time: datetime, end_time: datetime) -> int:
        """
        Calculates billable duration:
        - Minimum billable duration is 1 hour.
        - Partial hours are rounded UP to next whole hour.
        """
        if end_time <= start_time:
            raise ValueError("End time must be strictly after start time.")
        
        diff = end_time - start_time
        total_seconds = diff.total_seconds()
        hours = total_seconds / 3600.0
        
        billable_hours = math.ceil(hours)
        return max(1, billable_hours)

    @classmethod
    def calculate_price(cls, billable_hours: int, custom_rate: float = None) -> tuple[float, float]:
        """
        Calculates parking charge based on hourly rate.
        Returns: (hourly_rate, total_amount)
        """
        rate = custom_rate if custom_rate is not None else current_app.config.get('HOURLY_RATE', 30.0)
        total = billable_hours * rate
        return rate, round(total, 2)

    @classmethod
    def generate_booking_reference(cls) -> str:
        """Generates human-readable, unique booking reference."""
        date_prefix = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"BK-{date_prefix}-{random_suffix}"

    @classmethod
    def is_slot_available_for_period(cls, slot_id: int, start_time: datetime, end_time: datetime,
                                     exclude_booking_id: int = None) -> bool:
        """
        Checks if a slot is free of overlapping bookings during [start_time, end_time].
        Excludes cancelled or expired bookings.
        """
        slot = db.session.get(ParkingSlot, slot_id)
        if not slot or slot.status == 'MAINTENANCE':
            return False

        start_naive = to_naive_utc(start_time)
        end_naive = to_naive_utc(end_time)

        # Exclude expired pending bookings older than 15 minutes
        expiration_cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)

        # Overlapping condition: (A.start < B.end) AND (A.end > B.start)
        query = Booking.query.filter(
            Booking.slot_id == slot_id,
            Booking.status.in_(['CONFIRMED', 'CHECKED_IN', 'PENDING_PAYMENT']),
            Booking.start_time < end_naive,
            Booking.end_time > start_naive
        )

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        overlapping = query.all()

        for b in overlapping:
            # If it's a stale pending payment booking, we consider it expired
            b_created = to_naive_utc(b.created_at)
            if b.status == 'PENDING_PAYMENT' and b_created and b_created < expiration_cutoff:
                continue
            return False

        return True

    @classmethod
    def create_booking(cls, user_id: int, slot_id: int, vehicle_number: str,
                       start_time: datetime, duration_hours: int) -> Booking:
        """
        Validates timing, checks for concurrency/overlapping conflicts,
        and creates a new Booking in PENDING_PAYMENT status.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_naive = to_naive_utc(start_time)

        # Start time sanity check (allow up to 10 min in the past for clock skew)
        if start_naive < now - timedelta(minutes=10):
            raise ValueError("Booking start time cannot be in the past.")

        if duration_hours < 1:
            raise ValueError("Duration must be at least 1 hour.")

        end_naive = start_naive + timedelta(hours=duration_hours)

        # Database-level slot check
        slot = db.session.get(ParkingSlot, slot_id)
        if not slot:
            raise ValueError("Selected parking slot does not exist.")

        if slot.status == 'MAINTENANCE':
            raise ValueError(f"Slot {slot.slot_number} is currently undergoing maintenance.")

        # Check availability for this time slot
        if not cls.is_slot_available_for_period(slot_id, start_naive, end_naive):
            raise ValueError(f"Slot {slot.slot_number} is already reserved or occupied for the selected timeframe.")

        # Pricing calculation
        hourly_rate, total_amount = cls.calculate_price(duration_hours, slot.hourly_rate)
        booking_ref = cls.generate_booking_reference()

        booking = Booking(
            booking_reference=booking_ref,
            user_id=user_id,
            slot_id=slot_id,
            vehicle_number=vehicle_number.strip().upper(),
            start_time=start_naive,
            end_time=end_naive,
            duration_hours=duration_hours,
            hourly_rate=hourly_rate,
            total_amount=total_amount,
            status='PENDING_PAYMENT'
        )

        db.session.add(booking)
        db.session.commit()

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action='BOOKING_CREATED',
            details=f"Created booking {booking_ref} for slot {slot.slot_number} ({duration_hours}h, ₹{total_amount:.2f})"
        )
        db.session.add(audit)
        db.session.commit()

        return booking

    @classmethod
    def check_in(cls, booking: Booking, admin_user_id: int = None) -> Booking:
        """Performs physical check-in for an active confirmed booking."""
        if booking.status != 'CONFIRMED':
            raise ValueError(f"Cannot check in booking with status '{booking.status}'. Must be CONFIRMED.")

        booking.status = 'CHECKED_IN'
        booking.checked_in_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if booking.slot:
            booking.slot.status = 'OCCUPIED'

        db.session.commit()

        audit = AuditLog(
            user_id=admin_user_id or booking.user_id,
            action='CHECK_IN_PERFORMED',
            details=f"Vehicle {booking.vehicle_number} checked in to slot {booking.slot.slot_number if booking.slot else 'N/A'} for booking {booking.booking_reference}"
        )
        db.session.add(audit)
        db.session.commit()

        return booking

    @classmethod
    def check_out(cls, booking: Booking, admin_user_id: int = None) -> Booking:
        """Performs vehicle exit / check-out."""
        if booking.status not in ('CONFIRMED', 'CHECKED_IN'):
            raise ValueError(f"Cannot check out booking with status '{booking.status}'.")

        booking.status = 'COMPLETED'
        booking.checked_out_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Restore slot status to AVAILABLE if no immediate active bookings
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        has_upcoming = Booking.query.filter(
            Booking.slot_id == booking.slot_id,
            Booking.id != booking.id,
            Booking.status.in_(['CONFIRMED', 'CHECKED_IN']),
            Booking.start_time <= now + timedelta(minutes=30),
            Booking.end_time >= now
        ).first()

        if booking.slot:
            booking.slot.status = 'RESERVED' if has_upcoming else 'AVAILABLE'

        db.session.commit()

        audit = AuditLog(
            user_id=admin_user_id or booking.user_id,
            action='CHECK_OUT_PERFORMED',
            details=f"Vehicle {booking.vehicle_number} checked out for booking {booking.booking_reference}. Slot {booking.slot.slot_number if booking.slot else 'N/A'} freed."
        )
        db.session.add(audit)
        db.session.commit()

        return booking

    @classmethod
    def cancel_booking(cls, booking: Booking, user_id: int) -> Booking:
        """Cancels a booking if permitted by policy."""
        if booking.status in ('COMPLETED', 'CANCELLED', 'EXPIRED'):
            raise ValueError(f"Booking is already {booking.status} and cannot be cancelled.")

        if booking.status == 'CHECKED_IN':
            raise ValueError("Vehicle is already checked in. Please check out instead of cancelling.")

        booking.status = 'CANCELLED'
        booking.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        if booking.slot:
            # Check if other active booking exists
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            other_active = Booking.query.filter(
                Booking.slot_id == booking.slot_id,
                Booking.id != booking.id,
                Booking.status.in_(['CONFIRMED', 'CHECKED_IN']),
                Booking.start_time <= now,
                Booking.end_time >= now
            ).first()
            booking.slot.status = 'OCCUPIED' if other_active else 'AVAILABLE'

        db.session.commit()

        audit = AuditLog(
            user_id=user_id,
            action='BOOKING_CANCELLED',
            details=f"Booking {booking.booking_reference} cancelled."
        )
        db.session.add(audit)
        db.session.commit()

        return booking

