from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.admin_routes import admin_bp
from routes.parking_routes import parking_bp
from routes.booking_routes import booking_bp
from routes.payment_routes import payment_bp
from routes.qr_routes import qr_bp

__all__ = [
    'auth_bp',
    'user_bp',
    'admin_bp',
    'parking_bp',
    'booking_bp',
    'payment_bp',
    'qr_bp'
]

