/**
 * User Dashboard Logic - Drives live database statistics and bookings
 */

document.addEventListener('DOMContentLoaded', () => {
    loadUserDashboardSummary();
    loadZoneAvailability();
    loadRecentBookings();
});

async function loadUserDashboardSummary() {
    try {
        const response = await fetch('/api/user/dashboard-summary');
        const data = await response.json();

        if (!response.ok || !data.success) {
            showToast('Error', 'Unable to retrieve dashboard metrics.', 'danger');
            return;
        }

        // 1. Populate Metrics
        const fm = data.facility_metrics;
        document.getElementById('totalSlotsCount').textContent = fm.total_slots;
        document.getElementById('availableSlotsCount').textContent = fm.available_slots;
        document.getElementById('occupiedSlotsCount').textContent = fm.occupied_slots;
        document.getElementById('historyTripsCount').textContent = data.user_metrics.history_count;

        // 2. Populate Active Booking Spotlight
        const container = document.getElementById('activeBookingContainer');
        const active = data.user_metrics.active_booking;

        if (active) {
            const statusClass = active.status === 'CHECKED_IN' ? 'badge-checked-in' : 'badge-confirmed';
            const statusLabel = active.status === 'CHECKED_IN' ? 'Vehicle In Bay' : 'Active Pass (Reserved)';

            container.innerHTML = `
                <div class="card active-booking-card">
                    <div class="active-booking-badge">
                        <span class="badge ${statusClass}">
                            <i class="fa-solid fa-circle-dot"></i> ${statusLabel}
                        </span>
                    </div>
                    <div class="active-booking-content">
                        <div class="slot-badge-big">
                            <span>SLOT</span>
                            <strong>${escapeHtml(active.slot_number)}</strong>
                        </div>
                        <div class="active-details">
                            <h3>Reservation Ref: <span class="mono">${escapeHtml(active.booking_reference)}</span></h3>
                            <div class="active-meta">
                                <div><i class="fa-solid fa-location-dot text-cyan"></i> ${escapeHtml(active.slot_zone)} (${escapeHtml(active.slot_floor)})</div>
                                <div><i class="fa-solid fa-car text-amber"></i> Vehicle: <strong class="mono">${escapeHtml(active.vehicle_number)}</strong></div>
                                <div><i class="fa-solid fa-clock text-primary"></i> ${active.duration_hours} Hours</div>
                                <div><i class="fa-solid fa-indian-rupee-sign text-emerald"></i> Paid: ₹${parseFloat(active.total_amount).toFixed(2)}</div>
                            </div>
                            <p class="text-secondary" style="font-size: 0.85rem;">
                                Valid From: <strong>${formatLocalDateTime(active.start_time)}</strong> &rarr; Valid Until: <strong>${formatLocalDateTime(active.end_time)}</strong>
                            </p>
                        </div>
                        <div class="active-actions">
                            <a href="/confirmation/${active.id}" class="btn btn-primary">
                                <i class="fa-solid fa-qrcode"></i> View QR Pass
                            </a>
                            <a href="/pass/${active.id}/print" target="_blank" class="btn btn-outline btn-sm">
                                <i class="fa-solid fa-print"></i> Print Ticket
                            </a>
                        </div>
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div class="card" style="background-color: var(--bg-card); border: 1px dashed var(--border-card); text-align: center; padding: 2.5rem 1.5rem;">
                    <div style="font-size: 2.5rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                        <i class="fa-solid fa-car-tunnel"></i>
                    </div>
                    <h3 style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.35rem;">No Active Parking Session</h3>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; max-width: 480px; margin: 0 auto 1.5rem;">
                        You do not currently have a vehicle checked into the facility. Reserve a guaranteed parking slot in advance.
                    </p>
                    <a href="/slots" class="btn btn-primary">
                        <i class="fa-solid fa-plus-circle"></i> Browse Available Slots Now
                    </a>
                </div>
            `;
        }
    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

async function loadZoneAvailability() {
    try {
        const response = await fetch('/api/parking/availability');
        const data = await response.json();

        if (!response.ok || !data.success) return;

        const listEl = document.getElementById('zonesAvailabilityList');
        if (!data.zones || data.zones.length === 0) {
            listEl.innerHTML = '<p class="text-muted">No zones registered.</p>';
            return;
        }

        listEl.innerHTML = data.zones.map(z => {
            const isHigh = z.occupancy_percentage >= 75;
            return `
                <div class="zone-item">
                    <div class="zone-item-header">
                        <span>${escapeHtml(z.zone)}</span>
                        <span><strong>${z.available}</strong> free / ${z.total} slots (${z.occupancy_percentage}%)</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill ${isHigh ? 'high' : ''}" style="width: ${z.occupancy_percentage}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('Zone availability error:', err);
    }
}

async function loadRecentBookings() {
    try {
        const response = await fetch('/api/bookings/my');
        const data = await response.json();

        if (!response.ok || !data.success) return;

        const listEl = document.getElementById('recentBookingsList');
        const allBookings = [
            ...(data.active_bookings || []),
            ...(data.pending_bookings || []),
            ...(data.history_bookings || [])
        ].slice(0, 5);

        if (allBookings.length === 0) {
            listEl.innerHTML = `
                <div style="text-align: center; padding: 2rem 1rem; color: var(--text-muted);">
                    <i class="fa-solid fa-clipboard-list" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                    <p>No bookings found. Reserve your first parking slot today!</p>
                </div>
            `;
            return;
        }

        listEl.innerHTML = `
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Ref</th>
                            <th>Slot</th>
                            <th>Vehicle</th>
                            <th>Time</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${allBookings.map(b => `
                            <tr>
                                <td class="mono" style="font-weight: 700; color: var(--text-primary);">${escapeHtml(b.booking_reference)}</td>
                                <td><span class="badge badge-neutral">${escapeHtml(b.slot_number)}</span></td>
                                <td class="mono">${escapeHtml(b.vehicle_number)}</td>
                                <td>${formatLocalDateTime(b.start_time)}</td>
                                <td>
                                    <span class="badge badge-${b.status.toLowerCase()}">${escapeHtml(b.status)}</span>
                                </td>
                                <td>
                                    ${b.status === 'PENDING_PAYMENT' 
                                        ? `<a href="/payment/${b.id}" class="btn btn-primary btn-sm"><i class="fa-solid fa-credit-card"></i> Pay Now</a>`
                                        : `<a href="/confirmation/${b.id}" class="btn btn-outline btn-sm"><i class="fa-solid fa-qrcode"></i> Pass</a>`
                                    }
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (err) {
        console.error('Bookings load error:', err);
    }
}

