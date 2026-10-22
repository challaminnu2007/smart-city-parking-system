import uuid
from datetime import datetime, timezone
from flask import current_app
from database.db import db
from models.notification import Notification
from models.booking import Booking

class SMSService:
    @classmethod
    def send_booking_confirmation(cls, booking: Booking) -> Notification:
        """
        Sends SMS booking confirmation to user's registered mobile number.
        Uses Twilio if credentials are configured in environment;
        otherwise logs to the notification table as a development simulator record.
        Prevents duplicate SMS sends for the same booking.
        """
        user = booking.user
        mobile = user.mobile_number if user else booking.user_mobile

        # Check for existing successful/sent notification for this booking to prevent duplicates
        existing_sent = Notification.query.filter_by(
            booking_id=booking.id,
            status='SENT'
        ).first()
        if existing_sent:
            return existing_sent

        start_str = booking.start_time.strftime('%Y-%m-%d %H:%M')
        end_str = booking.end_time.strftime('%Y-%m-%d %H:%M')
        slot_number = booking.slot.slot_number if booking.slot else 'N/A'
        location = booking.slot.zone if booking.slot else 'Main Parking'

        message_body = (
            f"Smart Parking: Your booking is confirmed! "
            f"Booking ID: {booking.booking_reference}. "
            f"Slot: {slot_number}. "
            f"Location: {location}. "
            f"Vehicle: {booking.vehicle_number}. "
            f"Duration: {booking.duration_hours} hours. "
            f"Entry: {start_str}. "
            f"Exit: {end_str}. "
            f"Amount paid: ₹{booking.total_amount:.2f}. "
            f"Your parking QR pass is available in your dashboard."
        )

        account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        from_phone = current_app.config.get('TWILIO_PHONE_NUMBER')

        # Check if Twilio credentials are configured
        if account_sid and auth_token and from_phone:
            try:
                from twilio.rest import Client
                client = Client(account_sid, auth_token)
                
                # Format to E.164 if missing country code
                target_phone = mobile
                if not target_phone.startswith('+'):
                    target_phone = f"+91{target_phone}"  # Default to Indian country code
                
                twilio_msg = client.messages.create(
                    body=message_body,
                    from_=from_phone,
                    to=target_phone
                )
                
                notif = Notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    mobile_number=mobile,
                    message=message_body,
                    provider='TWILIO',
                    provider_ref=twilio_msg.sid,
                    status='SENT'
                )
                db.session.add(notif)
                db.session.commit()
                return notif
            except Exception as e:
                notif = Notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    mobile_number=mobile,
                    message=message_body,
                    provider='TWILIO',
                    provider_ref=None,
                    status='FAILED',
                    error_message=str(e)
                )
                db.session.add(notif)
                db.session.commit()
                return notif
        else:
            # Twilio credentials not provided -> Local Development Notification Simulator
            dev_ref = f"SIM-SMS-{uuid.uuid4().hex[:10].upper()}"
            notif = Notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                mobile_number=mobile,
                message=message_body,
                provider='LOCAL_DEV_LOG',
                provider_ref=dev_ref,
                status='DEV_SIMULATED',
                error_message='Twilio credentials not configured in .env. Logged in local notification repository.'
            )
            db.session.add(notif)
            db.session.commit()
            return notif

    @classmethod
    def retry_notification(cls, notification_id: int) -> tuple[bool, str]:
        """Retries sending a previously failed SMS notification."""
        notif = Notification.query.get(notification_id)
        if not notif:
            return False, "Notification record not found."

        if notif.status == 'SENT':
            return True, "Notification was already sent successfully."

        account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        from_phone = current_app.config.get('TWILIO_PHONE_NUMBER')

        if not (account_sid and auth_token and from_phone):
            return False, "Cannot send SMS: Twilio credentials are not configured in .env"

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            target_phone = notif.mobile_number
            if not target_phone.startswith('+'):
                target_phone = f"+91{target_phone}"
                
            twilio_msg = client.messages.create(
                body=notif.message,
                from_=from_phone,
                to=target_phone
            )
            
            notif.status = 'SENT'
            notif.provider = 'TWILIO'
            notif.provider_ref = twilio_msg.sid
            notif.error_message = None
            db.session.commit()
            return True, f"SMS sent successfully via Twilio (SID: {twilio_msg.sid})"
        except Exception as e:
            notif.status = 'FAILED'
            notif.error_message = str(e)
            db.session.commit()
            return False, f"Twilio delivery failed: {str(e)}"

