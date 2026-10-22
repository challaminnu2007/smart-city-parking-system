/**
 * Payment Processing Client Engine - Razorpay & Local Development Simulator
 */

async function initiateRazorpayPayment() {
    const bookingId = document.getElementById('currentBookingId').value;
    const btn = document.getElementById('razorpayPayBtn');
    const originalText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Contacting Payment Gateway...';

    try {
        // Step 1: Create Order on backend
        const orderRes = await fetch('/api/payments/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ booking_id: parseInt(bookingId, 10) })
        });

        const orderData = await orderRes.json();

        if (!orderRes.ok || !orderData.success) {
            showToast('Gateway Error', orderData.message || 'Could not initiate payment order.', 'danger');
            btn.disabled = false;
            btn.innerHTML = originalText;
            return;
        }

        const order = orderData.order;

        // Step 2: Open Razorpay modal
        const options = {
            key: order.key_id,
            amount: order.amount_paise,
            currency: order.currency,
            name: "Smart Parking Management System",
            description: `Parking Pass: ${order.booking_reference}`,
            order_id: order.order_id,
            handler: async function (response) {
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying Cryptographic Signature...';
                
                try {
                    // Step 3: Verify Signature on server
                    const verifyRes = await fetch('/api/payments/verify', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            booking_id: parseInt(bookingId, 10),
                            is_simulated: false,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_signature: response.razorpay_signature
                        })
                    });

                    const verifyData = await verifyRes.json();

                    if (verifyRes.ok && verifyData.success) {
                        showToast('Payment Verified!', 'Generating your secure QR parking pass...', 'success', 2000);
                        setTimeout(() => {
                            window.location.href = verifyData.redirect_url;
                        }, 1200);
                    } else {
                        showToast('Verification Failed', verifyData.message || 'Signature rejected by server.', 'danger', 4500);
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    }
                } catch (err) {
                    showToast('Network Error', 'Error validating payment with server.', 'danger');
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            },
            modal: {
                ondismiss: function () {
                    showToast('Payment Cancelled', 'Transaction was cancelled. You can retry anytime before expiration.', 'warning');
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            },
            prefill: {
                name: order.customer_name || '',
                email: order.customer_email || '',
                contact: order.customer_contact || ''
            },
            notes: {
                booking_reference: order.booking_reference,
                slot_number: order.slot_number || ''
            },
            theme: {
                color: "#2563eb"
            }
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', function (failureResponse) {
            const errDesc = (failureResponse.error && failureResponse.error.description) 
                ? failureResponse.error.description 
                : 'Payment transaction failed or was declined.';
            showToast('Payment Declined', errDesc, 'danger', 5000);
            btn.disabled = false;
            btn.innerHTML = originalText;
        });
        rzp.open();

    } catch (err) {
        showToast('Network Error', 'Failed to reach payment service.', 'danger');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function initiateSimulatedPayment() {
    const bookingId = document.getElementById('currentBookingId').value;
    const btn = document.getElementById('simPayBtn');
    const originalText = btn.innerHTML;

    const channelEl = document.querySelector('input[name="simChannel"]:checked');
    const method = channelEl ? channelEl.value : 'UPI';

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initializing Development Order...';

    try {
        // Step 1: Create Order in Simulator mode
        const orderRes = await fetch('/api/payments/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ booking_id: parseInt(bookingId, 10) })
        });

        const orderData = await orderRes.json();

        if (!orderRes.ok || !orderData.success) {
            showToast('Simulator Error', orderData.message || 'Could not create test order.', 'danger');
            btn.disabled = false;
            btn.innerHTML = originalText;
            return;
        }

        const simOrderId = orderData.order.order_id;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying Simulated Transaction...';

        // Step 2: Verify simulated payment
        const verifyRes = await fetch('/api/payments/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                booking_id: parseInt(bookingId, 10),
                is_simulated: true,
                order_id: simOrderId,
                payment_method: method
            })
        });

        const verifyData = await verifyRes.json();

        if (verifyRes.ok && verifyData.success) {
            showToast('Payment Verified (Simulated)', 'Test transaction confirmed! Generating QR pass & logging SMS...', 'success', 2500);
            setTimeout(() => {
                window.location.href = verifyData.redirect_url;
            }, 1200);
        } else {
            showToast('Simulator Error', verifyData.message || 'Simulation verification failed.', 'danger', 4500);
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    } catch (err) {
        showToast('Network Error', 'Connection failed during simulation checkout.', 'danger');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

async function cancelPendingBooking(bookingId) {
    if (!confirm('Are you sure you want to cancel this reservation? The slot will be released.')) {
        return;
    }

    try {
        const response = await fetch(`/api/bookings/${bookingId}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast('Reservation Cancelled', 'The pending slot reservation has been cancelled.', 'info');
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            showToast('Error', data.message || 'Failed to cancel reservation.', 'danger');
        }
    } catch (err) {
        showToast('Network Error', 'Could not reach server to cancel booking.', 'danger');
    }
}

