import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.db import db
from config import TestConfig
from models.user import User

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as client:
        with app.app_context():
            yield client
            db.session.remove()
            db.drop_all()

def test_user_registration_success(client):
    response = client.post('/api/auth/register', json={
        'full_name': 'Test User',
        'username': 'testdriver',
        'email': 'driver@example.com',
        'mobile_number': '9876543210',
        'vehicle_number': 'AP09AB9999',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['user']['username'] == 'testdriver'

def test_user_registration_duplicate_username(client):
    client.post('/api/auth/register', json={
        'full_name': 'First User',
        'username': 'unique_user',
        'email': 'unique1@example.com',
        'mobile_number': '9876543211',
        'vehicle_number': 'AP09AB1111',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    })
    
    dup_res = client.post('/api/auth/register', json={
        'full_name': 'Second User',
        'username': 'unique_user',
        'email': 'unique2@example.com',
        'mobile_number': '9876543212',
        'vehicle_number': 'AP09AB2222',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    })
    assert dup_res.status_code == 409

def test_user_login_and_logout(client):
    client.post('/api/auth/register', json={
        'full_name': 'Login Driver',
        'username': 'logindriver',
        'email': 'login@example.com',
        'mobile_number': '9123456789',
        'vehicle_number': 'TS09XY1234',
        'password': 'SecretPassword123',
        'confirm_password': 'SecretPassword123'
    })

    # Successful login
    login_res = client.post('/api/auth/login', json={
        'identifier': 'logindriver',
        'password': 'SecretPassword123'
    })
    assert login_res.status_code == 200
    assert login_res.get_json()['success'] is True

    # Check current user me endpoint
    me_res = client.get('/api/auth/me')
    assert me_res.status_code == 200
    assert me_res.get_json()['user']['username'] == 'logindriver'

    # Logout
    logout_res = client.post('/api/auth/logout')
    assert logout_res.status_code == 200

def test_default_admin_login(client):
    admin_res = client.post('/api/auth/login', json={
        'identifier': 'admin@smartparking.com',
        'password': 'Admin@12345'
    })
    assert admin_res.status_code == 200
    data = admin_res.get_json()
    assert data['user']['role'] == 'ADMIN'
    assert data['user']['full_name'] == 'Pournami'

