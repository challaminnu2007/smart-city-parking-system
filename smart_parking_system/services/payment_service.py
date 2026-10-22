import uuid
import hmac
import hashlib
from datetime import datetime, timezone
from flask import current_app
from database.db import db
from models.booking import Booking
from models.payment import Payment
from models.parking_slot import ParkingSlot
from models.audit_log import AuditLog
from services.qr_service import QRService
from services.sms_service import SMSService

class PaymentService:
    @classmethod
    def is_razorpay_configured(cls) -> bool:
        """Returns True if valid Razorpay API keys are present in application config."""
        key_id = current_app.config.get('RAZORPAY_KEY_ID', '').strip()
        key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '').strip()
        return bool(key_id and key_secret)

    @classmethod
    def create_payment_order(cls, booking: Booking) -> dict:
        """
        Creates a payment order.
        If Razorpay is configured, initializes a real Razorpay Order.
        Otherwise, returns a clearly-labelled Local Development Payment Simulator order.
        """
        if booking.status != 'PENDING_PAYMENT':
            raise ValueError(f"Cannot create payment order for booking with status '{booking.status}'.")

        amount_in_inr = booking.total_amount
        amount_in_paise = int(round(amount_in_inr * 100))

        # Check existing payment record
        existing_payment = Payment.query.filter_by(booking_id=booking.id).first()

        if cls.is_razorpay_configured():
            import razorpay
            client = razorpay.Client(auth=(
                current_app.config['RAZORPAY_KEY_ID'],
                current_app.config['RAZORPAY_KEY_SECRET']
            ))

            order_data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f"rcpt_{booking.booking_reference}",
                'notes': {
                    'booking_id': str(booking.id),
                    'booking_reference': booking.booking_reference,
                    'slot_number': booking.slot.slot_number if booking.slot else 'N/A',
                    'vehicle_number': booking.vehicle_number
                }
            }

            razorpay_order = client.order.create(data=order_data)
            order_id = razorpay_order['id']

            if not existing_payment:
                payment = Payment(
                    booking_id=booking.id,
                    user_id=booking.user_id,
                    payment_reference=f"PENDING-{order_id}",
                    order_reference=order_id,
                    amount=amount_in_inr,
                    currency='INR',
                    payment_method='RAZORPAY',
                    payment_gateway='RAZORPAY',
                    status='PENDING',
                    is_simulated=False
                )
                db.session.add(payment)
            else:
                existing_payment.payment_reference = f"PENDING-{order_id}"
                existing_payment.order_reference = order_id
                existing_payment.amount = amount_in_inr
                existing_payment.status = 'PENDING'
                existing_payment.payment_method = 'RAZORPAY'
                existing_payment.payment_gateway = 'RAZORPAY'
                existing_payment.is_simulated = False

            db.session.commit()

            return {
                'is_simulated': False,
                'gateway': 'RAZORPAY',
                'key_id': current_app.config['RAZORPAY_KEY_ID'],
                'order_id': order_id,
                'amount': amount_in_inr,
                'amount_paise': amount_in_paise,
                'currency': 'INR',
                'booking_reference': booking.booking_reference,
                'customer_name': booking.user.full_name if booking.user else '',
                'customer_email': booking.user.email if booking.user else '',
                'customer_contact': booking.user.mobile_number if booking.user else '',
                'slot_number': booking.slot.slot_number if booking.slot else 'N/A'
            }
        else:
            # Local Development Payment Simulator
            sim_order_id = f"order_sim_{uuid.uuid4().hex[:12]}"
            
            if not existing_payment:
                payment = Payment(
                    booking_id=booking.id,
                    user_id=booking.user_id,
                    payment_reference=f"SIM-PENDING-{sim_order_id}",
                    order_reference=sim_order_id,
                    amount=amount_in_inr,
                    currency='INR',
                    payment_method='DEV_SIMULATOR',
                    payment_gateway='LOCAL_DEV_SIMULATOR',
                    status='PENDING',
                    is_simulated=True
                )
                db.session.add(payment)
            else:
                existing_payment.payment_reference = f"SIM-PENDING-{sim_order_id}"
                existing_payment.order_reference = sim_order_id
                existing_payment.amount = amount_in_inr
                existing_payment.status = 'PENDING'
                existing_payment.payment_method = 'DEV_SIMULATOR'
                existing_payment.payment_gateway = 'LOCAL_DEV_SIMULATOR'
                existing_payment.is_simulated = True

            db.session.commit()

            return {
                'is_simulated': True,
                'gateway': 'LOCAL_DEV_SIMULATOR',
                'key_id': 'dev_simulated_key',
                'order_id': sim_order_id,
                'amount': amount_in_inr,
                'amount_paise': amount_in_paise,
                'currency': 'INR',
                'booking_reference': booking.booking_reference,
                'customer_name': booking.user.full_name if booking.user else '',
                'customer_email': booking.user.email if booking.user else '',
                'customer_contact': booking.user.mobile_number if booking.user else '',
                'slot_number': booking.slot.slot_number if booking.slot else 'N/A',
                'notice': 'Razorpay API keys not configured in .env. Running securely in Local Development Payment Simulator.'
            }

    @classmethod
    def verify_razorpay_payment(cls, booking: Booking, payment_id: str, order_id: str, signature: str) -> dict:
        """Verifies Razorpay HMAC signature and confirms booking."""
        if not cls.is_razorpay_configured():
            raise ValueError("Razorpay credentials are not configured in system environment.")

        secret = current_app.config['RAZORPAY_KEY_SECRET']
        
        # Verify HMAC-SHA256 signature using constant-time comparison
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        generated_signature = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(generated_signature, signature):
            # Mark payment as failed
            payment = Payment.query.filter_by(booking_id=booking.id).first()
            if payment:
                payment.status = 'FAILED'
                payment.gateway_signature = signature
                db.session.commit()
            raise ValueError("Payment signature verification failed. Transaction rejected.")

        # Payment is genuine & verified
        return cls._finalize_successful_payment(
            booking=booking,
            payment_ref=payment_id,
            order_ref=order_id,
            method='RAZORPAY',
            gateway='RAZORPAY',
            signature=signature,
            is_simulated=False
        )

    @classmethod
    def verify_simulated_payment(cls, booking: Booking, sim_order_id: str, method: str = 'UPI_MOCK') -> dict:
        """
        Verifies and finalizes a payment via the Local Development Payment Simulator.
        Clearly tags the transaction as simulated.
        """
        payment = Payment.query.filter_by(booking_id=booking.id).first()
        if not payment or payment.order_reference != sim_order_id:
            raise ValueError("Invalid simulator order reference.")

        sim_payment_id = f"pay_sim_{uuid.uuid4().hex[:14]}"

        return cls._finalize_successful_payment(
            booking=booking,
            payment_ref=sim_payment_id,
            order_ref=sim_order_id,
            method=f"SIMULATED_{method.upper()}",
            gateway='LOCAL_DEV_SIMULATOR',
            signature=f"sim_sig_{uuid.uuid4().hex[:16]}",
            is_simulated=True
        )

    @classmethod
    def _finalize_successful_payment(cls, booking: Booking, payment_ref: str, order_ref: str,
                                     method: str, gateway: str, signature: str, is_simulated: bool) -> dict:
        """
        Idempotent payment finalization:
        1. Confirms payment record as SUCCESS
        2. Updates booking to CONFIRMED
        3. Updates slot status
        4. Generates QR Pass with cryptographic HMAC
        5. Sends SMS notification
        6. Creates Audit Log entry
        """
        # Concurrency/idempotence check
        if booking.status == 'CONFIRMED' and booking.payment and booking.payment.status == 'SUCCESS':
            return {
                'success': True,
                'already_processed': True,
                'booking': booking.to_dict(),
                'payment': booking.payment.to_dict()
            }

        payment = Payment.query.filter_by(booking_id=booking.id).first()
        if not payment:
            payment = Payment(
                booking_id=booking.id,
                user_id=booking.user_id,
                amount=booking.total_amount,
                currency='INR'
            )
            db.session.add(payment)

        payment.payment_reference = payment_ref
        payment.order_reference = order_ref
        payment.payment_method = method
        payment.payment_gateway = gateway
        payment.gateway_signature = signature
        payment.status = 'SUCCESS'
        payment.is_simulated = is_simulated
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        payment.updated_at = now_naive

        # Update Booking
        booking.status = 'CONFIRMED'
        booking.updated_at = now_naive

        # Update slot status to RESERVED
        slot = booking.slot
        if slot and slot.status == 'AVAILABLE':
            slot.status = 'RESERVED'

        # Generate QR code pass
        qr_data, qr_img = QRService.generate_qr_for_booking(booking)
        booking.qr_code_data = qr_data
        booking.qr_code_image = qr_img

        db.session.commit()

        # Send SMS Confirmation
        sms_notif = SMSService.send_booking_confirmation(booking)

        # Log Audit Trail
        audit = AuditLog(
            user_id=booking.user_id,
            action='PAYMENT_CONFIRMED',
            details=f"Payment {payment_ref} verified (₹{booking.total_amount:.2f}). Booking {booking.booking_reference} confirmed. Gateway: {gateway} (Simulated: {is_simulated}). SMS Status: {sms_notif.status}."
        )
        db.session.add(audit)
        db.session.commit()

        return {
            'success': True,
            'booking': booking.to_dict(),
            'payment': payment.to_dict(),
            'sms_status': sms_notif.status,
            'is_simulated': is_simulated
        }

