import csv
import io
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, jsonify, session, Response
from database.db import db
from models.user import User
from models.parking_slot import ParkingSlot
from models.booking import Booking
from models.payment import Payment
from models.notification import Notification
from models.audit_log import AuditLog
from routes.auth_routes import admin_required
from services.sms_service import SMSService

admin_bp = Blueprint('admin', __name__)

# --- HTML Page Routes ---

@admin_bp.route('/admin')
@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard_page():
    """Main administrative dashboard."""
    user = db.session.get(User, session['user_id'])
    return render_template('admin_dashboard.html', user=user)


@admin_bp.route('/admin/slots')
@admin_required
def slots_management_page():
    """Admin parking slots CRUD interface."""
    return render_template('admin_slots.html')


@admin_bp.route('/admin/users')
@admin_required
def users_management_page():
    """Admin user account management and lookup."""
    return render_template('admin_users.html')


@admin_bp.route('/admin/bookings')
@admin_required
def bookings_management_page():
    """Admin booking oversight, cancellation, and QR gate checks."""
    return render_template('admin_bookings.html')


@admin_bp.route('/admin/payments')
@admin_required
def payments_management_page():
    """Admin payment verification and revenue reporting."""
    return render_template('admin_payments.html')


@admin_bp.route('/admin/analytics')
@admin_required
def analytics_page():
    """Admin visual analytics and Chart.js reporting."""
    return render_template('admin_analytics.html')


# --- REST API Endpoints ---

@admin_bp.route('/api/admin/dashboard', methods=['GET'])
@admin_required
def api_admin_summary():
    """
    Computes system-wide operational metrics strictly from database records:
    - Slot counts by status
    - User count
    - Total bookings count
    - Successful payments count
    - Total revenue (calculated exclusively from verified SUCCESS payments)
    """
    total_slots = ParkingSlot.query.count()
    available_slots = ParkingSlot.query.filter_by(status='AVAILABLE').count()
    reserved_slots = ParkingSlot.query.filter_by(status='RESERVED').count()
    occupied_slots = ParkingSlot.query.filter_by(status='OCCUPIED').count()
    maintenance_slots = ParkingSlot.query.filter_by(status='MAINTENANCE').count()

    total_users = User.query.filter_by(role='USER').count()
    total_bookings = Booking.query.count()
    
    successful_payments_count = Payment.query.filter_by(status='SUCCESS').count()
    
    # Revenue sum strictly from verified SUCCESS payments
    revenue_res = db.session.query(db.func.sum(Payment.amount)).filter(Payment.status == 'SUCCESS').scalar()
    total_revenue = round(float(revenue_res or 0.0), 2)

    # Active bookings right now
    now = datetime.now(timezone.utc)
    active_now = Booking.query.filter(
        Booking.status.in_(['CONFIRMED', 'CHECKED_IN']),
        Booking.start_time <= now,
        Booking.end_time >= now
    ).count()

    # Recent 5 bookings
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()

    return jsonify({
        'success': True,
        'metrics': {
            'total_slots': total_slots,
            'available_slots': available_slots,
            'reserved_slots': reserved_slots,
            'occupied_slots': occupied_slots,
            'maintenance_slots': maintenance_slots,
            'total_users': total_users,
            'total_bookings': total_bookings,
            'active_now': active_now,
            'successful_payments': successful_payments_count,
            'total_revenue': total_revenue
        },
        'recent_bookings': [b.to_dict() for b in recent_bookings]
    }), 200


@admin_bp.route('/api/admin/slots', methods=['GET'])
@admin_required
def api_admin_get_slots():
    """Fetch all parking slots with detailed administrative status."""
    slots = ParkingSlot.query.order_by(ParkingSlot.slot_number.asc()).all()
    return jsonify({
        'success': True,
        'slots': [s.to_dict() for s in slots]
    }), 200


@admin_bp.route('/api/admin/slots', methods=['POST'])
@admin_required
def api_admin_create_slot():
    """Add a new parking slot."""
    data = request.get_json() or {}
    slot_number = (data.get('slot_number') or '').strip().upper()
    zone = (data.get('zone') or '').strip()
    floor = (data.get('floor') or 'Ground').strip()
    slot_type = (data.get('slot_type') or 'Standard').strip()
    status = (data.get('status') or 'AVAILABLE').strip().upper()
    hourly_rate = data.get('hourly_rate', 30.0)

    if not slot_number or not zone:
        return jsonify({'error': 'Validation Error', 'message': 'Slot number and zone are required.'}), 400

    if ParkingSlot.query.filter_by(slot_number=slot_number).first():
        return jsonify({'error': 'Conflict', 'message': f'Slot {slot_number} already exists.'}), 409

    try:
        hourly_rate = float(hourly_rate)
    except ValueError:
        hourly_rate = 30.0

    slot = ParkingSlot(
        slot_number=slot_number,
        zone=zone,
        floor=floor,
        slot_type=slot_type,
        status=status,
        hourly_rate=hourly_rate,
        is_sample=False
    )
    db.session.add(slot)
    db.session.commit()

    audit = AuditLog(
        user_id=session['user_id'],
        action='SLOT_CREATED',
        details=f"Admin created slot {slot_number} ({zone}, {slot_type})"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Slot created successfully.', 'slot': slot.to_dict()}), 201


@admin_bp.route('/api/admin/slots/<int:slot_id>', methods=['PUT'])
@admin_required
def api_admin_update_slot(slot_id):
    """Update slot details or status."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    data = request.get_json() or {}

    if 'slot_number' in data and data['slot_number']:
        new_num = data['slot_number'].strip().upper()
        if new_num != slot.slot_number:
            if ParkingSlot.query.filter_by(slot_number=new_num).first():
                return jsonify({'error': 'Conflict', 'message': f'Slot {new_num} already exists.'}), 409
            slot.slot_number = new_num

    if 'zone' in data and data['zone']:
        slot.zone = data['zone'].strip()
    if 'floor' in data and data['floor']:
        slot.floor = data['floor'].strip()
    if 'slot_type' in data and data['slot_type']:
        slot.slot_type = data['slot_type'].strip()
    if 'status' in data and data['status']:
        slot.status = data['status'].strip().upper()
    if 'hourly_rate' in data:
        try:
            slot.hourly_rate = float(data['hourly_rate'])
        except ValueError:
            pass

    db.session.commit()

    audit = AuditLog(
        user_id=session['user_id'],
        action='SLOT_UPDATED',
        details=f"Admin updated slot {slot.slot_number} to status {slot.status}"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Slot updated successfully.', 'slot': slot.to_dict()}), 200


@admin_bp.route('/api/admin/slots/<int:slot_id>', methods=['DELETE'])
@admin_required
def api_admin_delete_slot(slot_id):
    """Safely delete parking slot, preventing deletion if active bookings exist."""
    slot = ParkingSlot.query.get_or_404(slot_id)

    # Check for active bookings
    active_booking = Booking.query.filter(
        Booking.slot_id == slot.id,
        Booking.status.in_(['CONFIRMED', 'CHECKED_IN', 'PENDING_PAYMENT'])
    ).first()

    if active_booking:
        return jsonify({
            'error': 'Conflict',
            'message': f'Cannot delete slot {slot.slot_number} because it has active or confirmed bookings.'
        }), 409

    slot_num = slot.slot_number
    db.session.delete(slot)
    db.session.commit()

    audit = AuditLog(
        user_id=session['user_id'],
        action='SLOT_DELETED',
        details=f"Admin deleted slot {slot_num}"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Slot {slot_num} deleted safely.'}), 200


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_get_users():
    """Search and view registered users."""
    search = request.args.get('search', '').strip()
    query = User.query

    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.mobile_number.ilike(f'%{search}%')) |
            (User.vehicle_number.ilike(f'%{search}%'))
        )

    users = query.order_by(User.created_at.desc()).all()
    
    users_data = []
    for u in users:
        d = u.to_dict()
        d['total_bookings'] = u.bookings.count()
        users_data.append(d)

    return jsonify({'success': True, 'users': users_data}), 200


@admin_bp.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def api_admin_toggle_user_status(user_id):
    """Activate or deactivate user account."""
    user = User.query.get_or_404(user_id)
    if user.id == session['user_id']:
        return jsonify({'error': 'Bad Request', 'message': 'Administrators cannot deactivate their own account.'}), 400

    user.is_active = not user.is_active
    db.session.commit()

    action_label = 'activated' if user.is_active else 'deactivated'
    audit = AuditLog(
        user_id=session['user_id'],
        action='USER_STATUS_TOGGLED',
        details=f"Admin {action_label} user account: {user.username}"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"User account {user.username} has been {action_label}.",
        'is_active': user.is_active
    }), 200


@admin_bp.route('/api/admin/bookings', methods=['GET'])
@admin_required
def api_admin_get_bookings():
    """Search, filter, and review all booking records."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()

    query = Booking.query

    if search:
        query = query.filter(
            (Booking.booking_reference.ilike(f'%{search}%')) |
            (Booking.vehicle_number.ilike(f'%{search}%'))
        )

    if status and status != 'ALL':
        query = query.filter(Booking.status == status)

    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Booking.start_time) == target_date)
        except ValueError:
            pass

    bookings = query.order_by(Booking.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(bookings),
        'bookings': [b.to_dict() for b in bookings]
    }), 200


@admin_bp.route('/api/admin/payments', methods=['GET'])
@admin_required
def api_admin_get_payments():
    """View payment records with filters."""
    status = request.args.get('status', '').strip()
    query = Payment.query

    if status and status != 'ALL':
        query = query.filter(Payment.status == status)

    payments = query.order_by(Payment.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(payments),
        'payments': [p.to_dict() for p in payments]
    }), 200


@admin_bp.route('/api/admin/payments/export', methods=['GET'])
@admin_required
def api_admin_export_payments():
    """Export payment transactions as a CSV report."""
    payments = Payment.query.order_by(Payment.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Payment ID', 'Payment Reference', 'Order Reference', 'Booking Reference',
        'Customer Name', 'Amount (INR)', 'Method', 'Gateway', 'Status', 'Simulated', 'Created At'
    ])

    for p in payments:
        writer.writerow([
            p.id,
            p.payment_reference,
            p.order_reference or 'N/A',
            p.booking.booking_reference if p.booking else 'N/A',
            p.user.full_name if p.user else 'N/A',
            p.amount,
            p.payment_method,
            p.payment_gateway,
            p.status,
            'Yes' if p.is_simulated else 'No',
            p.created_at.isoformat() if p.created_at else ''
        ])

    csv_data = output.getvalue()
    filename = f"smart_parking_payments_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@admin_bp.route('/api/admin/analytics', methods=['GET'])
@admin_required
def api_admin_analytics():
    """
    Supplies real aggregated data feeds for Chart.js visualizations:
    - Available vs Occupied vs Reserved vs Maintenance
    - Occupancy by Parking Zone
    - Daily booking counts (last 7 days)
    - Revenue trend over time (last 7 days)
    - Peak parking entry hours (0 - 23)
    - Booking status distribution
    - Most frequently booked slots
    """
    # 1. Slot status breakdown
    status_counts = {
        'Available': ParkingSlot.query.filter_by(status='AVAILABLE').count(),
        'Reserved': ParkingSlot.query.filter_by(status='RESERVED').count(),
        'Occupied': ParkingSlot.query.filter_by(status='OCCUPIED').count(),
        'Maintenance': ParkingSlot.query.filter_by(status='MAINTENANCE').count(),
    }

    # 2. Zone occupancy
    zone_stats = []
    zones = db.session.query(ParkingSlot.zone).distinct().all()
    for (z_name,) in zones:
        total_z = ParkingSlot.query.filter_by(zone=z_name).count()
        occ_z = ParkingSlot.query.filter(ParkingSlot.zone == z_name, ParkingSlot.status.in_(['OCCUPIED', 'RESERVED'])).count()
        zone_stats.append({
            'zone': z_name,
            'total': total_z,
            'occupied': occ_z
        })

    # 3. Last 7 days trend (daily bookings & revenue)
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    
    daily_labels = [d.strftime('%b %d') for d in days]
    daily_bookings = []
    daily_revenue = []

    for d in days:
        b_count = Booking.query.filter(db.func.date(Booking.created_at) == d).count()
        daily_bookings.append(b_count)

        rev_val = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'SUCCESS',
            db.func.date(Payment.created_at) == d
        ).scalar()
        daily_revenue.append(round(float(rev_val or 0.0), 2))

    # 4. Status distribution
    status_dist = {}
    for st in ['CONFIRMED', 'CHECKED_IN', 'COMPLETED', 'CANCELLED', 'PENDING_PAYMENT']:
        status_dist[st] = Booking.query.filter_by(status=st).count()

    # 5. Most booked slots
    top_slots_query = db.session.query(
        ParkingSlot.slot_number,
        db.func.count(Booking.id).label('booking_count')
    ).join(Booking, ParkingSlot.id == Booking.slot_id).group_by(ParkingSlot.slot_number).order_by(db.desc('booking_count')).limit(6).all()

    top_slots = [{'slot_number': r[0], 'count': r[1]} for r in top_slots_query]

    # 6. Peak hours (distribution of booking start hours)
    hourly_distribution = [0] * 24
    all_bookings = Booking.query.with_entities(Booking.start_time).all()
    for (st,) in all_bookings:
        if st:
            hourly_distribution[st.hour] += 1

    return jsonify({
        'success': True,
        'slot_status': status_counts,
        'zone_occupancy': zone_stats,
        'daily_trend': {
            'labels': daily_labels,
            'bookings': daily_bookings,
            'revenue': daily_revenue
        },
        'status_distribution': status_dist,
        'top_slots': top_slots,
        'peak_hours': {
            'labels': [f"{h:02d}:00" for h in range(24)],
            'counts': hourly_distribution
        }
    }), 200


@admin_bp.route('/api/admin/notifications', methods=['GET'])
@admin_required
def api_admin_get_notifications():
    """Returns SMS notifications log."""
    notifs = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()
    return jsonify({
        'success': True,
        'notifications': [n.to_dict() for n in notifs]
    }), 200


@admin_bp.route('/api/admin/notifications/<int:notification_id>/retry', methods=['POST'])
@admin_required
def api_admin_retry_notification(notification_id):
    """Retries a failed SMS notification."""
    success, message = SMSService.retry_notification(notification_id)
    return jsonify({'success': success, 'message': message}), (200 if success else 400)
