import pytest
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.db import db
from config import TestConfig
from models.user import User
from models.parking_slot import ParkingSlot
from models.booking import Booking
from models.payment import Payment
from models.notification import Notification
from services.qr_service import QRService

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.session.remove()
            db.drop_all()

def test_full_payment_and_qr_issuance_workflow(client):
    # 1. Register & Login Driver
    client.post('/api/auth/register', json={
        'full_name': 'Payment Tester',
        'username': 'paytester',
        'email': 'pay@test.com',
        'mobile_number': '8106479530',
        'vehicle_number': 'AP09ZZ8888',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    })
    client.post('/api/auth/login', json={'identifier': 'paytester', 'password': 'Password123!'})

    # 2. Find Available Slot
    slot = ParkingSlot.query.filter_by(status='AVAILABLE').first()
    future_start = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')

    # 3. Create Booking (PENDING_PAYMENT)
    book_res = client.post('/api/bookings', json={
        'slot_id': slot.id,
        'vehicle_number': 'AP09ZZ8888',
        'start_time': future_start,
        'duration_hours': 2
    })
    assert book_res.status_code == 201
    booking_id = book_res.get_json()['booking_id']

    booking = db.session.get(Booking, booking_id)
    assert booking.status == 'PENDING_PAYMENT'
    # QR code must NOT be generated yet
    assert booking.qr_code_image is None

    # 4. Create Payment Order
    order_res = client.post('/api/payments/create-order', json={'booking_id': booking_id})
    assert order_res.status_code == 200
    order_data = order_res.get_json()
    assert order_data['order']['is_simulated'] is True
    sim_order_id = order_data['order']['order_id']

    # 5. Verify Payment via Local Dev Simulator
    verify_res = client.post('/api/payments/verify', json={
        'booking_id': booking_id,
        'is_simulated': True,
        'order_id': sim_order_id,
        'payment_method': 'UPI'
    })
    assert verify_res.status_code == 200
    verify_data = verify_res.get_json()
    assert verify_data['success'] is True
    assert verify_data['is_simulated'] is True

    # 6. Check Database State
    db_booking = db.session.get(Booking, booking_id)
    assert db_booking.status == 'CONFIRMED'
    assert db_booking.payment is not None
    assert db_booking.payment.status == 'SUCCESS'
    assert db_booking.payment.is_simulated is True
    assert db_booking.qr_code_image is not None
    assert db_booking.qr_code_data is not None

    # 7. Check Notification Creation
    notif = Notification.query.filter_by(booking_id=booking_id).first()
    assert notif is not None
    assert notif.status in ('SENT', 'DEV_SIMULATED')
    assert 'Your booking is confirmed' in notif.message

    # 8. Check QR Validation Endpoint
    qr_val_res = client.post('/api/qr/validate', json={'qr_data': db_booking.qr_code_data})
    assert qr_val_res.status_code == 200
    assert qr_val_res.get_json()['valid'] is True


def test_razorpay_signature_verification_and_workflow(client):
    import hmac
    import hashlib
    from flask import current_app

    # Enable Razorpay keys for this test
    client.application.config['RAZORPAY_KEY_ID'] = 'rzp_test_Tqr63wNfTqM4sG'
    client.application.config['RAZORPAY_KEY_SECRET'] = 'g4D28OwiX3Nc4czARnCpRiic'

    # 1. Register & Login Driver
    client.post('/api/auth/register', json={
        'full_name': 'Razorpay Driver',
        'username': 'rzpdriver',
        'email': 'rzp@test.com',
        'mobile_number': '9876543210',
        'vehicle_number': 'TS09AA1234',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    })
    client.post('/api/auth/login', json={'identifier': 'rzpdriver', 'password': 'Password123!'})

    # 2. Book Slot
    slot = ParkingSlot.query.filter_by(status='AVAILABLE').first()
    future_start = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
    book_res = client.post('/api/bookings', json={
        'slot_id': slot.id,
        'vehicle_number': 'TS09AA1234',
        'start_time': future_start,
        'duration_hours': 3
    })
    assert book_res.status_code == 201
    booking_id = book_res.get_json()['booking_id']

    # 3. Create Razorpay Order
    order_res = client.post('/api/payments/create-order', json={'booking_id': booking_id})
    assert order_res.status_code == 200
    order_data = order_res.get_json()['order']
    assert order_data['gateway'] == 'RAZORPAY'
    assert order_data['is_simulated'] is False
    assert order_data['key_id'] == 'rzp_test_Tqr63wNfTqM4sG'
    assert order_data['order_id'].startswith('order_')

    order_id = order_data['order_id']
    fake_payment_id = 'pay_TestDemo12345678'

    # 4. Attempt Invalid Signature (should be rejected)
    bad_verify_res = client.post('/api/payments/verify', json={
        'booking_id': booking_id,
        'is_simulated': False,
        'razorpay_order_id': order_id,
        'razorpay_payment_id': fake_payment_id,
        'razorpay_signature': 'invalid_forged_signature_hex'
    })
    assert bad_verify_res.status_code == 400

    # 5. Compute Genuine HMAC-SHA256 Signature using Razorpay Secret
    secret = 'g4D28OwiX3Nc4czARnCpRiic'
    msg = f"{order_id}|{fake_payment_id}".encode('utf-8')
    valid_signature = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).hexdigest()

    # 6. Verify Genuine Signature
    good_verify_res = client.post('/api/payments/verify', json={
        'booking_id': booking_id,
        'is_simulated': False,
        'razorpay_order_id': order_id,
        'razorpay_payment_id': fake_payment_id,
        'razorpay_signature': valid_signature
    })
    assert good_verify_res.status_code == 200
    res_data = good_verify_res.get_json()
    assert res_data['success'] is True
    assert res_data['is_simulated'] is False

    # 7. Check database state
    db_booking = db.session.get(Booking, booking_id)
    assert db_booking.status == 'CONFIRMED'
    assert db_booking.payment.status == 'SUCCESS'
    assert db_booking.payment.payment_gateway == 'RAZORPAY'
    assert db_booking.payment.is_simulated is False
    assert db_booking.qr_code_image is not None

