from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from database.db import db
from models.booking import Booking
from models.payment import Payment
from routes.auth_routes import login_required
from services.payment_service import PaymentService

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payment/<int:booking_id>')
@login_required
def payment_page(booking_id):
    """Renders payment checkout page for a pending booking."""
    booking = db.get_or_404(Booking, booking_id)

    # Ownership check
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        flash('Unauthorized payment access.', 'danger')
        return redirect(url_for('user.dashboard_page'))

    if booking.status == 'CONFIRMED' and booking.payment and booking.payment.status == 'SUCCESS':
        flash('This booking has already been paid and confirmed.', 'info')
        return redirect(url_for('booking.confirmation_page', booking_id=booking.id))

    if booking.status in ('CANCELLED', 'EXPIRED'):
        flash(f'Cannot pay for a booking with status "{booking.status}".', 'warning')
        return redirect(url_for('user.dashboard_page'))

    is_razorpay_ready = PaymentService.is_razorpay_configured()
    return render_template('payment.html', booking=booking, is_razorpay_ready=is_razorpay_ready)


@payment_bp.route('/api/payments/create-order', methods=['POST'])
@login_required
def api_create_order():
    """Initializes payment order with Razorpay or local development simulator."""
    data = request.get_json() or {}
    booking_id = data.get('booking_id')

    if not booking_id:
        return jsonify({'error': 'Validation Error', 'message': 'booking_id is required.'}), 400

    booking = db.get_or_404(Booking, booking_id)

    # Ownership check
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return jsonify({'error': 'Forbidden', 'message': 'Unauthorized payment attempt.'}), 403

    try:
        order_info = PaymentService.create_payment_order(booking)
        return jsonify({'success': True, 'order': order_info}), 200
    except ValueError as ve:
        return jsonify({'error': 'Bad Request', 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Payment Gateway Error', 'message': str(e)}), 500


@payment_bp.route('/api/payments/verify', methods=['POST'])
@login_required
def api_verify_payment():
    """
    Verifies payment signature from Razorpay or authenticates simulated local test transaction.
    Generates QR parking pass and triggers SMS upon verification.
    """
    data = request.get_json() or {}
    booking_id = data.get('booking_id')

    if not booking_id:
        return jsonify({'error': 'Validation Error', 'message': 'booking_id is required.'}), 400

    booking = db.get_or_404(Booking, booking_id)

    # Ownership check
    if booking.user_id != session['user_id'] and session.get('role') != 'ADMIN':
        return jsonify({'error': 'Forbidden', 'message': 'Unauthorized payment verification.'}), 403

    is_simulated = data.get('is_simulated', False)

    try:
        if is_simulated:
            sim_order_id = data.get('order_id')
            payment_method = data.get('payment_method', 'UPI_MOCK')
            if not sim_order_id:
                return jsonify({'error': 'Validation Error', 'message': 'Simulator order ID missing.'}), 400

            result = PaymentService.verify_simulated_payment(
                booking=booking,
                sim_order_id=sim_order_id,
                method=payment_method
            )
        else:
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')

            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                return jsonify({'error': 'Validation Error', 'message': 'Missing Razorpay signature parameters.'}), 400

            result = PaymentService.verify_razorpay_payment(
                booking=booking,
                payment_id=razorpay_payment_id,
                order_id=razorpay_order_id,
                signature=razorpay_signature
            )

        result['redirect_url'] = url_for('booking.confirmation_page', booking_id=booking.id)
        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({'error': 'Verification Failed', 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal Processing Error', 'message': str(e)}), 500

