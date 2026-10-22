import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.db import db
from config import TestConfig
from models.parking_slot import ParkingSlot

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.session.remove()
            db.drop_all()

def test_get_parking_slots(client):
    res = client.get('/api/parking/slots')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['count'] > 0
    assert len(data['slots']) > 0

def test_slot_filters(client):
    # Filter by status
    res = client.get('/api/parking/slots?status=AVAILABLE')
    assert res.status_code == 200
    data = res.get_json()
    for s in data['slots']:
        assert s['status'] == 'AVAILABLE'

    # Filter by search
    res_search = client.get('/api/parking/slots?search=A-101')
    assert res_search.status_code == 200
    slots = res_search.get_json()['slots']
    assert len(slots) >= 1
    assert slots[0]['slot_number'] == 'A-101'

def test_parking_availability_metrics(client):
    res = client.get('/api/parking/availability')
    assert res.status_code == 200
    data = res.get_json()
    metrics = data['metrics']
    assert 'total' in metrics
    assert 'available' in metrics
    assert 'occupied' in metrics
    assert metrics['total'] == metrics['available'] + metrics['reserved'] + metrics['occupied'] + metrics['maintenance']
    assert len(data['zones']) > 0

