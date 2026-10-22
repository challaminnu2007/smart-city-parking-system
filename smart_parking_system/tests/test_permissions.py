import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.db import db
from config import TestConfig

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.session.remove()
            db.drop_all()

def test_unauthenticated_access_protection(client):
    # Unauthenticated user visiting protected pages/APIs
    res_dash = client.get('/dashboard')
    assert res_dash.status_code == 302  # redirects to login

    res_api = client.get('/api/auth/me')
    assert res_api.status_code == 401

    res_admin_api = client.get('/api/admin/dashboard')
    assert res_admin_api.status_code == 401

def test_user_cannot_access_admin_portal(client):
    # Register ordinary user
    client.post('/api/auth/register', json={
        'full_name': 'Normal User',
        'username': 'normaldriver',
        'email': 'normal@test.com',
        'mobile_number': '9876543210',
        'vehicle_number': 'TS09XY9999',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    })
    client.post('/api/auth/login', json={'identifier': 'normaldriver', 'password': 'Password123!'})

    # User can access User Dashboard
    user_dash = client.get('/dashboard')
    assert user_dash.status_code == 200

    # User cannot access Admin Dashboard page (403)
    admin_dash = client.get('/admin')
    assert admin_dash.status_code == 403

    # User cannot call Admin REST APIs (403)
    admin_api = client.get('/api/admin/dashboard')
    assert admin_api.status_code == 403

def test_admin_can_access_both_dashboards(client):
    # Login as default Admin (Pournami)
    client.post('/api/auth/login', json={
        'identifier': 'admin@smartparking.com',
        'password': 'Admin@12345'
    })

    # Admin access Admin Console
    admin_res = client.get('/admin')
    assert admin_res.status_code == 200

    # Admin can access User View / Dashboard
    user_view_res = client.get('/dashboard')
    assert user_view_res.status_code == 200

    # Admin can access admin APIs
    api_res = client.get('/api/admin/dashboard')
    assert api_res.status_code == 200
    assert api_res.get_json()['success'] is True

