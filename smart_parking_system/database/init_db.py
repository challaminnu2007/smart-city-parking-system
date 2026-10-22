import os
import sys
from datetime import datetime, timezone

# Ensure project root is in sys.path when executed directly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db import db
from models.user import User
from models.parking_slot import ParkingSlot
from models.audit_log import AuditLog

def seed_default_admin(app):
    """Safely seeds the default admin user if no admin user exists in the database."""
    admin_email = app.config.get('ADMIN_EMAIL', 'admin@smartparking.com')
    existing_admin = User.query.filter_by(role='ADMIN').first()
    
    if existing_admin:
        print(f"[DB INIT] Existing administrator '{existing_admin.username}' ({existing_admin.email}) found. Keeping intact.")
        return existing_admin

    admin_name = app.config.get('ADMIN_NAME', 'Pournami')
    admin_mobile = app.config.get('ADMIN_MOBILE', '8106479530')
    admin_password = app.config.get('ADMIN_PASSWORD', 'Admin@12345')
    admin_username = 'pournami_admin'

    admin = User(
        full_name=admin_name,
        username=admin_username,
        email=admin_email,
        mobile_number=admin_mobile,
        vehicle_number='AP09SMART01',
        role='ADMIN',
        is_active=True
    )
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()

    log = AuditLog(
        user_id=admin.id,
        action='SYSTEM_ADMIN_INITIALIZED',
        details=f"Default administrator account initialized with email {admin_email}"
    )
    db.session.add(log)
    db.session.commit()

    print(f"[DB INIT] Created default admin account: {admin.username} ({admin_email})")
    return admin


def seed_sample_parking_slots():
    """Seeds initial sample parking slots across diverse zones and vehicle categories."""
    if ParkingSlot.query.count() > 0:
        print("[DB INIT] Parking slots already exist. Preserving existing slot data.")
        return

    sample_slots = [
        # Zone A - Ground Floor (Standard & Accessible)
        {"slot_number": "A-101", "zone": "Zone A - Ground Floor", "floor": "Ground", "slot_type": "Standard", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "A-102", "zone": "Zone A - Ground Floor", "floor": "Ground", "slot_type": "Standard", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "A-103", "zone": "Zone A - Ground Floor", "floor": "Ground", "slot_type": "Standard", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "A-104", "zone": "Zone A - Ground Floor", "floor": "Ground", "slot_type": "Accessible", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "A-105", "zone": "Zone A - Ground Floor", "floor": "Ground", "slot_type": "Compact", "status": "AVAILABLE", "hourly_rate": 30.0},

        # Zone B - Level 1 (Sedans & SUVs)
        {"slot_number": "B-201", "zone": "Zone B - Level 1", "floor": "Level 1", "slot_type": "Standard", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "B-202", "zone": "Zone B - Level 1", "floor": "Level 1", "slot_type": "SUV", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "B-203", "zone": "Zone B - Level 1", "floor": "Level 1", "slot_type": "SUV", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "B-204", "zone": "Zone B - Level 1", "floor": "Level 1", "slot_type": "Compact", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "B-205", "zone": "Zone B - Level 1", "floor": "Level 1", "slot_type": "Standard", "status": "MAINTENANCE", "hourly_rate": 30.0},

        # Zone C - EV Charging Plaza (Level 2)
        {"slot_number": "C-301", "zone": "Zone C - EV Plaza", "floor": "Level 2", "slot_type": "EV Charging", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "C-302", "zone": "Zone C - EV Plaza", "floor": "Level 2", "slot_type": "EV Charging", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "C-303", "zone": "Zone C - EV Plaza", "floor": "Level 2", "slot_type": "EV Charging", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "C-304", "zone": "Zone C - EV Plaza", "floor": "Level 2", "slot_type": "Compact", "status": "AVAILABLE", "hourly_rate": 30.0},

        # Zone D - Executive / Basement Bay
        {"slot_number": "D-001", "zone": "Zone D - Executive Bay", "floor": "Basement", "slot_type": "SUV", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "D-002", "zone": "Zone D - Executive Bay", "floor": "Basement", "slot_type": "Standard", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "D-003", "zone": "Zone D - Executive Bay", "floor": "Basement", "slot_type": "Two-Wheeler", "status": "AVAILABLE", "hourly_rate": 30.0},
        {"slot_number": "D-004", "zone": "Zone D - Executive Bay", "floor": "Basement", "slot_type": "Two-Wheeler", "status": "AVAILABLE", "hourly_rate": 30.0},
    ]

    for item in sample_slots:
        slot = ParkingSlot(
            slot_number=item["slot_number"],
            zone=item["zone"],
            floor=item["floor"],
            slot_type=item["slot_type"],
            status=item["status"],
            hourly_rate=item["hourly_rate"],
            is_sample=True
        )
        db.session.add(slot)

    db.session.commit()
    print(f"[DB INIT] Seeded {len(sample_slots)} sample parking slots (clearly tagged is_sample=True).")


def init_database(app, reset=False):
    """Initializes database tables, creates directories, and seeds baseline records."""
    # Ensure instance directory exists for SQLite
    instance_dir = os.path.join(app.root_path, 'instance')
    os.makedirs(instance_dir, exist_ok=True)

    with app.app_context():
        if reset:
            print("[DB WARNING] Resetting all database tables! All existing records will be deleted.")
            db.drop_all()
        
        db.create_all()
        seed_default_admin(app)
        seed_sample_parking_slots()
        print("[DB INIT] Database initialization completed successfully.")


if __name__ == '__main__':
    from flask import Flask
    from config import Config

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    reset_flag = '--reset' in sys.argv
    if reset_flag:
        confirm = input("Are you sure you want to completely RESET the database? All data will be lost (y/N): ")
        if confirm.lower() != 'y':
            print("Database reset aborted.")
            sys.exit(0)

    init_database(app, reset=reset_flag)

