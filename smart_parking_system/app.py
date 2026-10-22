import os
import sys

# Ensure project root is in sys.path for direct or package execution
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from datetime import datetime, timezone
from flask import Flask, render_template, session, redirect, url_for, jsonify, request
from config import Config
from database.db import db
from database.init_db import init_database
from models.user import User

def create_app(config_class=Config):
    """Application factory for Smart Parking Management System."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.user_routes import user_bp
    from routes.admin_routes import admin_bp
    from routes.parking_routes import parking_bp
    from routes.booking_routes import booking_bp
    from routes.payment_routes import payment_bp
    from routes.qr_routes import qr_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(qr_bp)

    # Global Template Context Processor
    @app.context_processor
    def inject_global_template_vars():
        user = None
        if session.get('user_id'):
            user = db.session.get(User, session['user_id'])
        return {
            'current_user': user,
            'is_logged_in': bool(user),
            'is_admin': user.is_admin() if user else False,
            'system_hourly_rate': app.config.get('HOURLY_RATE', 30.0),
            'now_year': datetime.now(timezone.utc).year
        }

    # Root landing page route
    @app.route('/')
    def index():
        if session.get('user_id'):
            if session.get('role') == 'ADMIN':
                return redirect(url_for('admin.dashboard_page'))
            return redirect(url_for('user.dashboard_page'))
        return render_template('index.html')

    # Global Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to access this resource.'}), 403
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found on this server.'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred. Please try again.'}), 500
        return render_template('500.html'), 500

    # Auto-initialize database on application startup
    with app.app_context():
        try:
            init_database(app, reset=False)
        except Exception as e:
            app.logger.error(f"Error during automatic database initialization: {e}")

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
