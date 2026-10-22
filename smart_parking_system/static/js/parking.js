/**
 * Parking Slots Discovery & Real-Time Filter Engine
 */

let debounceTimer = null;
let initialFiltersLoaded = false;

document.addEventListener('DOMContentLoaded', () => {
    loadSlots();
});

function debounceSlots() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        loadSlots();
    }, 300);
}

async function loadSlots() {
    const search = document.getElementById('slotSearchInput').value.trim();
    const status = document.getElementById('statusFilter').value;
    const zone = document.getElementById('zoneFilter').value;
    const slotType = document.getElementById('typeFilter').value;

    const refreshBtn = document.getElementById('refreshSlotsBtn');
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
    }

    const grid = document.getElementById('slotsGrid');
    const params = new URLSearchParams();

    if (search) params.append('search', search);
    if (status) params.append('status', status);
    if (zone && zone !== 'ALL') params.append('zone', zone);
    if (slotType && slotType !== 'ALL') params.append('slot_type', slotType);

    try {
        const response = await fetch(`/api/parking/slots?${params.toString()}`);
        const data = await response.json();

        if (refreshBtn) {
            refreshBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Refresh Availability';
        }

        if (!response.ok || !data.success) {
            grid.innerHTML = '<div class="loading-state text-danger">Failed to load parking slots. Please retry.</div>';
            return;
        }

        document.getElementById('slotsCountLabel').textContent = data.count;

        // Populate filters on first load
        if (!initialFiltersLoaded && data.filters) {
            const zoneSelect = document.getElementById('zoneFilter');
            const typeSelect = document.getElementById('typeFilter');

            (data.filters.zones || []).forEach(z => {
                const opt = document.createElement('option');
                opt.value = z;
                opt.textContent = z;
                zoneSelect.appendChild(opt);
            });

            (data.filters.slot_types || []).forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                typeSelect.appendChild(opt);
            });

            initialFiltersLoaded = true;
        }

        // Render slots
        if (data.slots.length === 0) {
            grid.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-circle-question fa-2x" style="margin-bottom: 0.75rem; color: var(--text-muted);"></i>
                    <p>No parking slots match the selected criteria.</p>
                </div>
            `;
            return;
        }

        const typeIconMap = {
            'Standard': 'fa-car',
            'Compact': 'fa-car-side',
            'SUV': 'fa-truck-pickup',
            'EV Charging': 'fa-charging-station',
            'Accessible': 'fa-wheelchair',
            'Two-Wheeler': 'fa-motorcycle'
        };

        grid.innerHTML = data.slots.map(s => {
            const icon = typeIconMap[s.slot_type] || 'fa-car';
            const statusLower = s.status.toLowerCase();
            const isAvailable = s.status === 'AVAILABLE';

            return `
                <div class="slot-card status-${statusLower}">
                    <div class="slot-header">
                        <div class="slot-number">
                            <i class="fa-solid ${icon} text-primary"></i>
                            ${escapeHtml(s.slot_number)}
                        </div>
                        <span class="badge badge-${statusLower}">${escapeHtml(s.status)}</span>
                    </div>

                    <div class="slot-zone">
                        <i class="fa-solid fa-layer-group"></i> ${escapeHtml(s.zone)}
                    </div>

                    <div class="slot-meta">
                        <span><i class="fa-solid fa-building"></i> ${escapeHtml(s.floor)}</span>
                        <span>&bull;</span>
                        <span><i class="fa-solid fa-tag"></i> ${escapeHtml(s.slot_type)}</span>
                        ${s.is_sample ? `<span class="badge badge-neutral" style="font-size: 0.65rem;" title="Pre-seeded sample slot">Sample</span>` : ''}
                    </div>

                    <div class="slot-price">
                        ₹${parseFloat(s.hourly_rate).toFixed(2)} <span>/ billable hour</span>
                    </div>

                    <div>
                        ${isAvailable ? `
                            <a href="/book/${s.id}" class="btn btn-primary btn-block">
                                <i class="fa-solid fa-bookmark"></i> Book This Slot
                            </a>
                        ` : `
                            <button class="btn btn-secondary btn-block disabled" disabled>
                                <i class="fa-solid fa-ban"></i> Slot ${escapeHtml(s.status)}
                            </button>
                        `}
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        if (refreshBtn) refreshBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Refresh Availability';
        grid.innerHTML = '<div class="loading-state text-danger">Network error connecting to slot service.</div>';
    }
}

