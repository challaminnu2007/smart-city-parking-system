from datetime import datetime, timezone
from flask import Blueprint, render_template, session, jsonify
from database.db import db
from models.user import User
from models.parking_slot import ParkingSlot
from models.booking import Booking
from models.payment import Payment
from routes.auth_routes import login_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
@login_required
def dashboard_page():
    """User dashboard landing page."""
    user = db.session.get(User, session['user_id'])
    return render_template('user_dashboard.html', user=user)


@user_bp.route('/profile')
@login_required
def profile_page():
    """User profile and settings page."""
    user = db.session.get(User, session['user_id'])
    return render_template('profile.html', user=user)


@user_bp.route('/api/user/dashboard-summary', methods=['GET'])
@login_required
def api_dashboard_summary():
    """
    Returns live summary metrics for the user dashboard:
    - Real-time facility occupancy stats
    - User's active booking
    - Count of upcoming and past bookings
    - Recent payment status
    """
    user_id = session['user_id']
    now = datetime.now(timezone.utc)

    # Facility stats
    total_slots = ParkingSlot.query.count()
    available_slots = ParkingSlot.query.filter_by(status='AVAILABLE').count()
    occupied_slots = ParkingSlot.query.filter_by(status='OCCUPIED').count()
    reserved_slots = ParkingSlot.query.filter_by(status='RESERVED').count()

    # User active booking (confirmed or checked in, not yet ended)
    active_booking = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status.in_(['CONFIRMED', 'CHECKED_IN']),
        Booking.end_time >= now
    ).order_by(Booking.start_time.asc()).first()

    # User upcoming bookings
    upcoming_count = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status == 'CONFIRMED',
        Booking.start_time > now
    ).count()

    # User past bookings
    history_count = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status.in_(['COMPLETED', 'CANCELLED', 'EXPIRED'])
    ).count()

    # Pending payment count
    pending_count = Booking.query.filter(
        Booking.user_id == user_id,
        Booking.status == 'PENDING_PAYMENT'
    ).count()

    # Recent payments
    recent_payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.created_at.desc()).limit(5).all()

    return jsonify({
        'success': True,
        'user': {
            'id': session['user_id'],
            'full_name': session.get('full_name'),
            'username': session.get('username')
        },
        'facility_metrics': {
            'total_slots': total_slots,
            'available_slots': available_slots,
            'occupied_slots': occupied_slots,
            'reserved_slots': reserved_slots
        },
        'user_metrics': {
            'has_active_booking': bool(active_booking),
            'active_booking': active_booking.to_dict() if active_booking else None,
            'upcoming_count': upcoming_count,
            'history_count': history_count,
            'pending_payment_count': pending_count
        },
        'recent_payments': [p.to_dict() for p in recent_payments]
    }), 200
