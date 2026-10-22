import re
from functools import wraps
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from werkzeug.security import check_password_hash
from database.db import db
from models.user import User
from models.audit_log import AuditLog

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to require login for pages or API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required to access this resource.'}), 401
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login_page', next=request.path))
        
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            session.clear()
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Forbidden', 'message': 'Account is inactive or does not exist.'}), 403
            flash('Your account has been deactivated. Please contact support.', 'danger')
            return redirect(url_for('auth.login_page'))
            
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require administrator privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
            flash('Please log in as an administrator.', 'warning')
            return redirect(url_for('auth.login_page', next=request.path))

        user = db.session.get(User, user_id)
        if not user or not user.is_active or user.role != 'ADMIN':
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Forbidden', 'message': 'Administrative privileges required.'}), 403
            return render_template('403.html'), 403

        return f(*args, **kwargs)
    return decorated_function


# --- HTML Template Routes ---

@auth_bp.route('/login')
def login_page():
    if session.get('user_id'):
        if session.get('role') == 'ADMIN':
            return redirect(url_for('admin.dashboard_page'))
        return redirect(url_for('user.dashboard_page'))
    return render_template('login.html')


@auth_bp.route('/register')
def register_page():
    if session.get('user_id'):
        return redirect(url_for('user.dashboard_page'))
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        audit = AuditLog(user_id=user_id, action='USER_LOGOUT', details='User logged out.')
        db.session.add(audit)
        db.session.commit()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login_page'))


# --- REST API Endpoints ---

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or request.form
    
    full_name = (data.get('full_name') or '').strip()
    username = (data.get('username') or '').strip().lower()
    email = (data.get('email') or '').strip().lower()
    mobile_number = (data.get('mobile_number') or '').strip()
    vehicle_number = (data.get('vehicle_number') or '').strip().upper()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    # Backend field validations
    if not all([full_name, username, email, mobile_number, vehicle_number, password]):
        return jsonify({'error': 'Validation Error', 'message': 'All fields are required.'}), 400

    if len(username) < 3 or len(username) > 30 or not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return jsonify({'error': 'Validation Error', 'message': 'Username must be 3-30 alphanumeric characters.'}), 400

    # Email format validation
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'error': 'Validation Error', 'message': 'Please provide a valid email address.'}), 400

    # Mobile format validation (10 digits)
    cleaned_mobile = re.sub(r'[^0-9]', '', mobile_number)
    if len(cleaned_mobile) < 10 or len(cleaned_mobile) > 13:
        return jsonify({'error': 'Validation Error', 'message': 'Please provide a valid 10-digit mobile number.'}), 400

    # Vehicle number validation (min 5 alphanumeric characters)
    cleaned_vehicle = re.sub(r'[^a-zA-Z0-9]', '', vehicle_number)
    if len(cleaned_vehicle) < 4:
        return jsonify({'error': 'Validation Error', 'message': 'Please provide a valid vehicle registration number.'}), 400

    # Password validation
    if len(password) < 6:
        return jsonify({'error': 'Validation Error', 'message': 'Password must be at least 6 characters long.'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Validation Error', 'message': 'Passwords do not match.'}), 400

    # Check uniqueness
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Conflict', 'message': 'Username is already taken. Please choose another.'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Conflict', 'message': 'An account with this email address already exists.'}), 409

    # Registration is strictly for regular USER accounts (prevents self-escalation)
    new_user = User(
        full_name=full_name,
        username=username,
        email=email,
        mobile_number=cleaned_mobile,
        vehicle_number=vehicle_number,
        role='USER',
        is_active=True
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    # Log audit
    audit = AuditLog(
        user_id=new_user.id,
        action='USER_REGISTERED',
        details=f"New user registered: {username} ({email})"
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Registration successful! You can now log in.',
        'user': new_user.to_dict()
    }), 201


@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or request.form
    
    identifier = (data.get('identifier') or data.get('username') or '').strip().lower()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'error': 'Validation Error', 'message': 'Please provide both username/email and password.'}), 400

    # Find user by either username or email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Unauthorized', 'message': 'Invalid username/email or password.'}), 401

    if not user.is_active:
        return jsonify({'error': 'Forbidden', 'message': 'This account has been deactivated. Contact support.'}), 403

    # Set session
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['full_name'] = user.full_name
    session['role'] = user.role
    session.permanent = True

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action='USER_LOGIN_SUCCESS',
        details=f"User {user.username} logged in successfully."
    )
    db.session.add(audit)
    db.session.commit()

    redirect_target = url_for('admin.dashboard_page') if user.role == 'ADMIN' else url_for('user.dashboard_page')

    return jsonify({
        'success': True,
        'message': f"Welcome back, {user.full_name}!",
        'redirect_url': redirect_target,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    user_id = session.get('user_id')
    if user_id:
        audit = AuditLog(user_id=user_id, action='USER_LOGOUT_API', details='User logged out via API.')
        db.session.add(audit)
        db.session.commit()
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200


@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_get_current_user():
    user = db.session.get(User, session['user_id'])
    return jsonify({'success': True, 'user': user.to_dict()}), 200


@auth_bp.route('/api/auth/profile', methods=['PUT'])
@login_required
def api_update_profile():
    user = db.session.get(User, session['user_id'])
    data = request.get_json() or {}

    full_name = data.get('full_name', '').strip()
    mobile_number = data.get('mobile_number', '').strip()
    vehicle_number = data.get('vehicle_number', '').strip().upper()

    if full_name:
        user.full_name = full_name
        session['full_name'] = full_name
        
    if mobile_number:
        cleaned_mobile = re.sub(r'[^0-9]', '', mobile_number)
        if len(cleaned_mobile) >= 10:
            user.mobile_number = cleaned_mobile
        else:
            return jsonify({'error': 'Validation Error', 'message': 'Mobile number must be at least 10 digits.'}), 400

    if vehicle_number:
        user.vehicle_number = vehicle_number

    db.session.commit()

    audit = AuditLog(user_id=user.id, action='PROFILE_UPDATED', details="Profile details updated.")
    db.session.add(audit)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully.',
        'user': user.to_dict()
    }), 200


@auth_bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def api_change_password():
    user = db.session.get(User, session['user_id'])
    data = request.get_json() or {}

    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_new_password = data.get('confirm_new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'Validation Error', 'message': 'All password fields are required.'}), 400

    if not user.check_password(current_password):
        return jsonify({'error': 'Unauthorized', 'message': 'Current password is incorrect.'}), 401

    if len(new_password) < 6:
        return jsonify({'error': 'Validation Error', 'message': 'New password must be at least 6 characters.'}), 400

    if new_password != confirm_new_password:
        return jsonify({'error': 'Validation Error', 'message': 'New passwords do not match.'}), 400

    user.set_password(new_password)
    db.session.commit()

    audit = AuditLog(user_id=user.id, action='PASSWORD_CHANGED', details="Password changed successfully.")
    db.session.add(audit)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Password updated successfully.'}), 200
