from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from database.db import db
from models.booking import Booking
from models.parking_slot import ParkingSlot
from models.user import User
from routes.auth_routes import login_required
from services.booking_service import BookingService

booking_bp = Blueprint('booking', __name__)

# --- HTML Page Routes ---

@booking_bp.route('/book/<int:slot_id>')
@login_required
def booking_form_page(slot_id):
    """Render booking form for a selected slot."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    user = User.query.get(session['user_id'])
    
    if slot.status == 'MAINTENANCE':
        flash(f"Slot {slot.slot_number} is currently under maintenance.", 'danger')
        return redirect(url_for('parking.slots_page'))

    return render_template('booking.html', slot=slot, user=user)


@booking_bp.route('/my-bookings')
@login_required
def my_bookings_page():
    """Render active and upcoming bookings page."""
    return render_template('my_bookings.html')


@booking_bp.route('/parking-history')
@login_required
def parking_history_page():
    """Render completed and cancelled past parking history."""
    return render_template('parking_history.html')


@booking_bp.route('/confirmation/<int:booking_id>')
@login_required
def confirmation_page(booking_id):
    """Render booking confirmation page with QR parking pass."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ownership verification
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        flash('Unauthorized access to booking pass.', 'danger')
        return redirect(url_for('user.dashboard_page'))

    return render_template('booking_confirmation.html', booking=booking)


@booking_bp.route('/pass/<int:booking_id>/print')
@login_required
def pass_print_page(booking_id):
    """Print-friendly parking pass format."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return render_template('403.html'), 403
    return render_template('pass_print.html', booking=booking)


# --- REST API Endpoints ---

@booking_bp.route('/api/bookings', methods=['POST'])
@login_required
def api_create_booking():
    """Creates a new booking reservation and returns payment redirect."""
    data = request.get_json() or request.form
    user_id = session['user_id']

    slot_id = data.get('slot_id')
    vehicle_number = (data.get('vehicle_number') or '').strip().upper()
    start_time_raw = data.get('start_time')
    duration_hours = data.get('duration_hours')

    if not all([slot_id, vehicle_number, start_time_raw, duration_hours]):
        return jsonify({'error': 'Validation Error', 'message': 'All booking fields are required.'}), 400

    try:
        slot_id = int(slot_id)
        duration_hours = int(duration_hours)
        if duration_hours < 1:
            return jsonify({'error': 'Validation Error', 'message': 'Duration must be at least 1 hour.'}), 400
    except ValueError:
        return jsonify({'error': 'Validation Error', 'message': 'Invalid slot or duration format.'}), 400

    # Parse start_time (ISO or YYYY-MM-DDTHH:MM)
    try:
        # Replace Z with UTC offset if present
        clean_time_str = start_time_raw.replace('Z', '+00:00')
        start_time = datetime.fromisoformat(clean_time_str)
        if start_time.tzinfo is None:
            # Assume local/UTC
            start_time = start_time.replace(tzinfo=timezone.utc)
    except Exception:
        return jsonify({'error': 'Validation Error', 'message': 'Invalid start time format. Use YYYY-MM-DDTHH:MM.'}), 400

    try:
        booking = BookingService.create_booking(
            user_id=user_id,
            slot_id=slot_id,
            vehicle_number=vehicle_number,
            start_time=start_time,
            duration_hours=duration_hours
        )

        return jsonify({
            'success': True,
            'message': 'Slot reserved! Please complete the payment to confirm your booking.',
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'redirect_url': url_for('payment.payment_page', booking_id=booking.id),
            'booking': booking.to_dict()
        }), 201
    except ValueError as ve:
        return jsonify({'error': 'Booking Conflict', 'message': str(ve)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@booking_bp.route('/api/bookings/my', methods=['GET'])
@login_required
def api_get_my_bookings():
    """Retrieves all bookings for currently authenticated user."""
    user_id = session['user_id']
    now = datetime.now(timezone.utc)

    # Active / checked-in bookings
    active = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status.in_(['CONFIRMED', 'CHECKED_IN']),
        Booking.end_time >= now
    ).order_by(Booking.start_time.asc()).all()

    # Pending payment bookings
    pending = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status == 'PENDING_PAYMENT'
    ).order_by(Booking.created_at.desc()).all()

    # Past or completed/cancelled bookings
    history = Booking.query.filter(
        Booking.user_id == user_id,
        (Booking.status.in_(['COMPLETED', 'CANCELLED', 'EXPIRED'])) |
        (Booking.status.in_(['CONFIRMED', 'CHECKED_IN']) & (Booking.end_time < now))
    ).order_by(Booking.created_at.desc()).all()

    return jsonify({
        'success': True,
        'active_bookings': [b.to_dict() for b in active],
        'pending_bookings': [b.to_dict() for b in pending],
        'history_bookings': [b.to_dict() for b in history]
    }), 200


@booking_bp.route('/api/bookings/<int:booking_id>', methods=['GET'])
@login_required
def api_get_booking(booking_id):
    """Retrieve details of a single booking."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return jsonify({'error': 'Forbidden', 'message': 'You cannot access another user\'s booking.'}), 403

    return jsonify({'success': True, 'booking': booking.to_dict()}), 200


@booking_bp.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def api_cancel_booking(booking_id):
    """Cancels a booking according to cancellation rules."""
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return jsonify({'error': 'Forbidden', 'message': 'You cannot cancel another user\'s booking.'}), 403

    try:
        cancelled_booking = BookingService.cancel_booking(booking, session['user_id'])
        return jsonify({
            'success': True,
            'message': 'Booking cancelled successfully.',
            'booking': cancelled_booking.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'error': 'Bad Request', 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

