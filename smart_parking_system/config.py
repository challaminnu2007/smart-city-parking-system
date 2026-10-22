import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(basedir, '..'))
load_dotenv(os.path.join(parent_dir, '.env'))
load_dotenv(os.path.join(basedir, '.env'), override=True)

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-parking-default-secret-change-me')
    
    instance_dir = os.path.join(basedir, 'instance')
    try:
        os.makedirs(instance_dir, exist_ok=True)
    except OSError:
        instance_dir = os.path.join('/tmp', 'instance')
        try:
            os.makedirs(instance_dir, exist_ok=True)
        except OSError:
            pass
    default_db_path = os.path.join(instance_dir, 'smart_parking.db').replace('\\', '/')

    # Database URL with fallback to absolute SQLite in instance folder
    raw_db_url = os.environ.get('DATABASE_URL', '').strip()
    if raw_db_url and not raw_db_url.startswith('sqlite:///instance/'):
        # Compatibility fix for older postgres:// URI schemas
        if raw_db_url.startswith('postgres://'):
            raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{default_db_path}'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Pricing configuration
    HOURLY_RATE = float(os.environ.get('HOURLY_RATE', 30.0))
    
    # Default Admin Credentials
    ADMIN_NAME = os.environ.get('ADMIN_NAME', 'Pournami')
    ADMIN_MOBILE = os.environ.get('ADMIN_MOBILE', '8106479530')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@smartparking.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@12345')
    
    # Razorpay Credentials
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()
    
    # Twilio SMS Credentials
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '').strip()


class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RAZORPAY_KEY_ID = ''
    RAZORPAY_KEY_SECRET = ''
    TWILIO_ACCOUNT_SID = ''
