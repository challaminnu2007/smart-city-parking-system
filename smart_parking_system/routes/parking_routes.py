from flask import Blueprint, request, jsonify, render_template, session
from database.db import db
from models.parking_slot import ParkingSlot
from models.booking import Booking
from routes.auth_routes import login_required

parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/slots')
@login_required
def slots_page():
    """Render parking slots discovery and booking list page."""
    return render_template('parking_slots.html')


@parking_bp.route('/api/parking/slots', methods=['GET'])
def api_get_slots():
    """
    Returns list of parking slots with optional filtering:
    - search: by slot number or zone
    - zone: filter by specific parking zone
    - slot_type: Standard, Compact, SUV, EV Charging, Accessible
    - status: AVAILABLE, RESERVED, OCCUPIED, MAINTENANCE
    """
    search = request.args.get('search', '').strip()
    zone = request.args.get('zone', '').strip()
    slot_type = request.args.get('slot_type', '').strip()
    status = request.args.get('status', '').strip()

    query = ParkingSlot.query

    if search:
        query = query.filter(
            (ParkingSlot.slot_number.ilike(f'%{search}%')) |
            (ParkingSlot.zone.ilike(f'%{search}%')) |
            (ParkingSlot.floor.ilike(f'%{search}%'))
        )

    if zone and zone != 'ALL':
        query = query.filter(ParkingSlot.zone == zone)

    if slot_type and slot_type != 'ALL':
        query = query.filter(ParkingSlot.slot_type == slot_type)

    if status and status != 'ALL':
        query = query.filter(ParkingSlot.status == status)

    slots = query.order_by(ParkingSlot.slot_number.asc()).all()

    # Extract unique filter options dynamically from database
    all_zones = [z[0] for z in db.session.query(ParkingSlot.zone).distinct().all()]
    all_types = [t[0] for t in db.session.query(ParkingSlot.slot_type).distinct().all()]

    return jsonify({
        'success': True,
        'count': len(slots),
        'slots': [s.to_dict() for s in slots],
        'filters': {
            'zones': all_zones,
            'slot_types': all_types
        }
    }), 200


@parking_bp.route('/api/parking/slots/<int:slot_id>', methods=['GET'])
def api_get_slot(slot_id):
    """Retrieve details of a single parking slot."""
    slot = ParkingSlot.query.get_or_404(slot_id)
    return jsonify({
        'success': True,
        'slot': slot.to_dict()
    }), 200


@parking_bp.route('/api/parking/availability', methods=['GET'])
def api_get_availability():
    """
    Computes real-time parking availability metrics strictly from database records.
    Never returns hardcoded statistics.
    """
    total_slots = ParkingSlot.query.count()
    available_slots = ParkingSlot.query.filter_by(status='AVAILABLE').count()
    reserved_slots = ParkingSlot.query.filter_by(status='RESERVED').count()
    occupied_slots = ParkingSlot.query.filter_by(status='OCCUPIED').count()
    maintenance_slots = ParkingSlot.query.filter_by(status='MAINTENANCE').count()

    # Breakdown by zone
    zones_data = []
    zones = db.session.query(ParkingSlot.zone).distinct().all()
    for (zone_name,) in zones:
        z_total = ParkingSlot.query.filter_by(zone=zone_name).count()
        z_avail = ParkingSlot.query.filter_by(zone=zone_name, status='AVAILABLE').count()
        z_occ = ParkingSlot.query.filter_by(zone=zone_name, status='OCCUPIED').count()
        z_res = ParkingSlot.query.filter_by(zone=zone_name, status='RESERVED').count()
        zones_data.append({
            'zone': zone_name,
            'total': z_total,
            'available': z_avail,
            'occupied': z_occ,
            'reserved': z_res,
            'occupancy_percentage': round(((z_occ + z_res) / z_total * 100) if z_total > 0 else 0, 1)
        })

    return jsonify({
        'success': True,
        'metrics': {
            'total': total_slots,
            'available': available_slots,
            'reserved': reserved_slots,
            'occupied': occupied_slots,
            'maintenance': maintenance_slots,
            'occupancy_rate': round(((occupied_slots + reserved_slots) / total_slots * 100) if total_slots > 0 else 0, 1)
        },
        'zones': zones_data
    }), 200

