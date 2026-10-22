import base64
import io
from flask import Blueprint, request, jsonify, session, send_file, current_app
from database.db import db
from models.booking import Booking
from routes.auth_routes import login_required, admin_required
from services.qr_service import QRService
from services.booking_service import BookingService

qr_bp = Blueprint('qr', __name__)

@qr_bp.route('/api/bookings/<int:booking_id>/qr', methods=['GET'])
@login_required
def api_get_booking_qr(booking_id):
    """Retrieves QR code image and data for a verified booking."""
    booking = Booking.query.get_or_404(booking_id)

    # Ownership check
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return jsonify({'error': 'Forbidden', 'message': 'Access to another user\'s pass is denied.'}), 403

    if booking.status not in ('CONFIRMED', 'CHECKED_IN', 'COMPLETED'):
        return jsonify({'error': 'Bad Request', 'message': 'QR pass is only generated for confirmed, paid bookings.'}), 400

    # If QR code was not pre-generated, generate now
    if not booking.qr_code_image:
        qr_data, qr_img = QRService.generate_qr_for_booking(booking)
        booking.qr_code_data = qr_data
        booking.qr_code_image = qr_img
        db.session.commit()

    download_mode = request.args.get('download') == 'true'
    if download_mode and booking.qr_code_image:
        # Strip header if present
        data_parts = booking.qr_code_image.split(',')
        img_bytes = base64.b64decode(data_parts[-1])
        return send_file(
            io.BytesIO(img_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name=f"parking_pass_{booking.booking_reference}.png"
        )

    return jsonify({
        'success': True,
        'booking_reference': booking.booking_reference,
        'qr_data': booking.qr_code_data,
        'qr_image_data_uri': booking.qr_code_image
    }), 200


@qr_bp.route('/api/qr/validate', methods=['POST'])
@login_required
def api_validate_qr():
    """
    Validates QR parking pass data.
    Callable by admin or staff to verify entry eligibility.
    """
    data = request.get_json() or {}
    qr_payload = data.get('qr_data') or data.get('booking_reference')

    if not qr_payload:
        return jsonify({'error': 'Validation Error', 'message': 'No QR code payload provided.'}), 400

    result = QRService.validate_qr_code(qr_payload)
    status_code = 200 if result.get('valid') else 400
    return jsonify(result), status_code


@qr_bp.route('/api/qr/check-in', methods=['POST'])
@admin_required
def api_admin_check_in():
    """Admin endpoint to check in a vehicle upon gate arrival."""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')
    qr_data = data.get('qr_data')

    booking = None
    if booking_id:
        booking = Booking.query.get(booking_id)
    elif qr_data:
        res = QRService.validate_qr_code(qr_data)
        if res.get('valid') and res.get('booking_id'):
            booking = Booking.query.get(res['booking_id'])
        else:
            return jsonify({'error': 'Invalid Pass', 'message': res.get('error', 'Invalid QR code.')}), 400

    if not booking:
        return jsonify({'error': 'Not Found', 'message': 'Booking not found.'}), 404

    try:
        updated_booking = BookingService.check_in(booking, admin_user_id=session['user_id'])
        return jsonify({
            'success': True,
            'message': f"Vehicle {updated_booking.vehicle_number} checked in successfully at slot {updated_booking.slot.slot_number}.",
            'booking': updated_booking.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'error': 'Action Failed', 'message': str(ve)}), 400


@qr_bp.route('/api/qr/check-out', methods=['POST'])
@admin_required
def api_admin_check_out():
    """Admin endpoint to check out a vehicle upon exit."""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')

    booking = Booking.query.get_or_404(booking_id)
    try:
        updated_booking = BookingService.check_out(booking, admin_user_id=session['user_id'])
        return jsonify({
            'success': True,
            'message': f"Vehicle {updated_booking.vehicle_number} checked out successfully.",
            'booking': updated_booking.to_dict()
        }), 200
    except ValueError as ve:
        return jsonify({'error': 'Action Failed', 'message': str(ve)}), 400

