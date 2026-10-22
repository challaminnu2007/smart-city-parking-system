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
from services.booking_service import BookingService

@pytest.fixture
def client_and_app():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            yield client, app
            db.session.remove()
            db.drop_all()

def test_hourly_price_calculation(client_and_app):
    client, app = client_and_app
    
    # 1 hour = 30
    h1 = BookingService.calculate_billable_hours(
        datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
    )
    assert h1 == 1
    rate, total = BookingService.calculate_price(h1, 30.0)
    assert total == 30.0

    # 2 hours = 60
    h2 = BookingService.calculate_billable_hours(
        datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    )
    assert h2 == 2
    rate, total = BookingService.calculate_price(h2, 30.0)
    assert total == 60.0

    # Partial hours (1 hr 15 mins) rounded up to 2 hours = 60
    h_partial = BookingService.calculate_billable_hours(
        datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 11, 15, tzinfo=timezone.utc)
    )
    assert h_partial == 2
    rate, total = BookingService.calculate_price(h_partial, 30.0)
    assert total == 60.0

def test_create_booking_and_overlap_rejection(client_and_app):
    client, app = client_and_app

    # Create test driver
    client.post('/api/auth/register', json={
        'full_name': 'Driver One',
        'username': 'driver1',
        'email': 'driver1@test.com',
        'mobile_number': '9876543210',
        'vehicle_number': 'TS09AA1111',
        'password': 'Pass123456!',
        'confirm_password': 'Pass123456!'
    })

    client.post('/api/auth/login', json={'identifier': 'driver1', 'password': 'Pass123456!'})

    slot = ParkingSlot.query.filter_by(status='AVAILABLE').first()
    assert slot is not None

    future_start = (datetime.now(timezone.utc) + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')

    # Booking 1: from T+2 to T+4 (2 hours)
    b1_res = client.post('/api/bookings', json={
        'slot_id': slot.id,
        'vehicle_number': 'TS09AA1111',
        'start_time': future_start,
        'duration_hours': 2
    })
    assert b1_res.status_code == 201
    b1_data = b1_res.get_json()
    assert b1_data['booking']['total_amount'] == 60.0
    assert b1_data['booking']['status'] == 'PENDING_PAYMENT'

    # Booking 2: Overlapping attempt for same slot (e.g. from T+3 to T+5)
    overlap_start = (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M')
    b2_res = client.post('/api/bookings', json={
        'slot_id': slot.id,
        'vehicle_number': 'TS09AA2222',
        'start_time': overlap_start,
        'duration_hours': 2
    })
    # Must reject with Conflict 409
    assert b2_res.status_code == 409
    assert 'already reserved or occupied' in b2_res.get_json()['message']

def test_reject_past_booking_time(client_and_app):
    client, app = client_and_app

    client.post('/api/auth/register', json={
        'full_name': 'Driver Two',
        'username': 'driver2',
        'email': 'driver2@test.com',
        'mobile_number': '9876543211',
        'vehicle_number': 'TS09BB2222',
        'password': 'Pass123456!',
        'confirm_password': 'Pass123456!'
    })
    client.post('/api/auth/login', json={'identifier': 'driver2', 'password': 'Pass123456!'})

    slot = ParkingSlot.query.first()
    past_time = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M')

    past_res = client.post('/api/bookings', json={
        'slot_id': slot.id,
        'vehicle_number': 'TS09BB2222',
        'start_time': past_time,
        'duration_hours': 1
    })
    assert past_res.status_code == 409
    assert 'cannot be in the past' in past_res.get_json()['message']

