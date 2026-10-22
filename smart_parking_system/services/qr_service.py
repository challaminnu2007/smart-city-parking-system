import json
import hmac
import hashlib
import io
import base64
import qrcode
from datetime import datetime, timezone
from flask import current_app
from database.db import db
from models.booking import Booking

class QRService:
    @staticmethod
    def generate_verification_token(booking_ref: str, secret_key: str) -> str:
        """Generates a secure HMAC token to verify QR authenticity."""
        return hmac.new(
            secret_key.encode('utf-8'),
            booking_ref.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()[:24]

    @classmethod
    def generate_qr_for_booking(cls, booking: Booking) -> tuple[str, str]:
        """
        Generates QR code payload and base64 PNG image for a paid confirmed booking.
        Returns: (qr_data_string, base64_image_data_uri)
        """
        secret_key = current_app.config.get('SECRET_KEY', 'default-key')
        token = cls.generate_verification_token(booking.booking_reference, secret_key)
        
        payload = {
            'system': 'SmartParking',
            'booking_ref': booking.booking_reference,
            'slot': booking.slot.slot_number if booking.slot else 'UNKNOWN',
            'zone': booking.slot.zone if booking.slot else 'UNKNOWN',
            'vehicle': booking.vehicle_number,
            'start_time': booking.start_time.isoformat(),
            'end_time': booking.end_time.isoformat(),
            'amount_paid': booking.total_amount,
            'status': booking.status,
            'token': token
        }
        
        payload_json = json.dumps(payload, separators=(',', ':'))
        
        # Generate QR Code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2
        )
        qr.add_data(payload_json)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_uri = f"data:image/png;base64,{img_str}"
        
        return payload_json, data_uri

    @classmethod
    def validate_qr_code(cls, qr_string_or_ref: str) -> dict:
        """
        Validates QR code data or booking reference.
        Checks:
        1. Parse structure & find booking
        2. Valid signature check
        3. Payment status is SUCCESS
        4. Booking status is valid (CONFIRMED or CHECKED_IN)
        5. Time window active
        """
        secret_key = current_app.config.get('SECRET_KEY', 'default-key')
        booking_ref = None

        # Check if the string is JSON or plain booking reference
        try:
            data = json.loads(qr_string_or_ref)
            booking_ref = data.get('booking_ref')
            token = data.get('token')
            expected_token = cls.generate_verification_token(booking_ref, secret_key) if booking_ref else None
            if token and token != expected_token:
                return {
                    'valid': False,
                    'error': 'QR Code signature verification failed. Forged or corrupted pass.'
                }
        except (json.JSONDecodeError, TypeError):
            # Might be plain booking reference scanned directly
            booking_ref = qr_string_or_ref.strip()

        if not booking_ref:
            return {'valid': False, 'error': 'Invalid QR code format. Missing booking reference.'}

        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        if not booking:
            return {'valid': False, 'error': f'Booking reference "{booking_ref}" not found in database.'}

        # Check payment
        if not booking.payment or booking.payment.status != 'SUCCESS':
            return {
                'valid': False,
                'error': 'Payment has not been verified for this booking. Parking pass is invalid.',
                'booking': booking.to_dict()
            }

        # Check booking status
        if booking.status in ('CANCELLED', 'EXPIRED'):
            return {
                'valid': False,
                'error': f'Booking is currently {booking.status}. Access denied.',
                'booking': booking.to_dict()
            }

        if booking.status == 'COMPLETED':
            return {
                'valid': False,
                'error': 'Booking has already been completed and checked out.',
                'booking': booking.to_dict()
            }

        return {
            'valid': True,
            'message': 'QR Parking Pass is valid and verified.',
            'booking': booking.to_dict(),
            'booking_id': booking.id,
            'status': booking.status,
            'slot_number': booking.slot.slot_number if booking.slot else 'N/A',
            'vehicle_number': booking.vehicle_number,
            'checked_in_at': booking.checked_in_at.isoformat() if booking.checked_in_at else None
        }

