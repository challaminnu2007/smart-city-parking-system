/**
 * Booking Client Script - Date pre-fill, dynamic pricing calculations, and reservation submission
 */

document.addEventListener('DOMContentLoaded', () => {
    initDateTimeInputs();
    recalculatePrice();
});

function initDateTimeInputs() {
    const startInput = document.getElementById('startTime');
    if (!startInput) return;

    // Set default start time to now + 5 minutes
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5);

    // Format to YYYY-MM-DDTHH:MM local format
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');

    const formattedNow = `${year}-${month}-${day}T${hours}:${minutes}`;
    startInput.value = formattedNow;
    startInput.min = formattedNow;
}

function recalculatePrice() {
    const rate = parseFloat(document.getElementById('slotHourlyRate').value || 30.0);
    const duration = parseInt(document.getElementById('durationHours').value || 1, 10);
    const startInput = document.getElementById('startTime');

    const total = duration * rate;

    document.getElementById('calcRate').textContent = `₹${rate.toFixed(2)}`;
    document.getElementById('calcDuration').textContent = `${duration} Hour${duration > 1 ? 's' : ''}`;
    document.getElementById('calcFormula').textContent = `${duration} × ₹${rate.toFixed(2)}`;
    document.getElementById('calcTotal').textContent = `₹${total.toFixed(2)}`;

    // Calculate exit preview
    const exitPreview = document.getElementById('expectedExitPreview');
    if (startInput && startInput.value) {
        try {
            const start = new Date(startInput.value);
            const exit = new Date(start.getTime() + duration * 3600 * 1000);
            exitPreview.textContent = exit.toLocaleString(undefined, {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });
        } catch {
            exitPreview.textContent = 'Invalid start time selected';
        }
    }
}

async function handleCreateBooking(e) {
    e.preventDefault();
    const btn = document.getElementById('bookingSubmitBtn');
    const originalText = btn.innerHTML;

    const slotId = document.getElementById('slotId').value;
    const vehicleNumber = document.getElementById('vehicleNumber').value.trim().toUpperCase();
    const startTimeRaw = document.getElementById('startTime').value;
    const durationHours = document.getElementById('durationHours').value;

    if (!slotId || !vehicleNumber || !startTimeRaw || !durationHours) {
        showToast('Incomplete Form', 'Please complete all reservation fields.', 'warning');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking Availability & Reserving...';

    try {
        const response = await fetch('/api/bookings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                slot_id: parseInt(slotId, 10),
                vehicle_number: vehicleNumber,
                start_time: startTimeRaw,
                duration_hours: parseInt(durationHours, 10)
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast('Slot Held!', 'Slot temporarily reserved. Proceeding to payment checkout...', 'success', 2000);
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1000);
        } else {
            showToast('Reservation Failed', data.message || 'Could not complete reservation.', 'danger', 4500);
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (err) {
        showToast('Network Error', 'Unable to communicate with the reservation service.', 'danger');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

