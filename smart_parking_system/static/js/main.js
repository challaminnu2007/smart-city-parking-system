/**
 * SMART PARKING MANAGEMENT SYSTEM - CORE CLIENT JAVASCRIPT
 */

// Mobile Navigation Toggle
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('show');
            const icon = navToggle.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-bars');
                icon.classList.toggle('fa-xmark');
            }
        });
    }

    // User Dropdown Menu
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userDropdownMenu = document.getElementById('userDropdownMenu');

    if (userMenuBtn && userDropdownMenu) {
        userMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdownMenu.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!userDropdownMenu.contains(e.target) && !userMenuBtn.contains(e.target)) {
                userDropdownMenu.classList.remove('show');
            }
        });
    }

    // Process Flask Flash Messages as Modern Toasts
    const flashContainer = document.getElementById('flashMessagesData');
    if (flashContainer) {
        const flashes = flashContainer.querySelectorAll('span');
        flashes.forEach(span => {
            const type = span.dataset.type || 'info';
            const message = span.dataset.message || '';
            const titleMap = {
                'success': 'Success',
                'danger': 'Attention',
                'warning': 'Warning',
                'info': 'Notice'
            };
            showToast(titleMap[type] || 'Notice', message, type);
        });
    }
});

/**
 * Shows modern toast message (replaces browser alerts completely)
 */
function showToast(title, message, type = 'info', duration = 4500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const iconMap = {
        'success': 'fa-solid fa-circle-check',
        'danger': 'fa-solid fa-circle-exclamation',
        'warning': 'fa-solid fa-triangle-exclamation',
        'info': 'fa-solid fa-circle-info'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="${iconMap[type] || iconMap.info}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-close" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 250);
    });

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(50px)';
                setTimeout(() => toast.remove(), 250);
            }
        }, duration);
    }
}

/**
 * Modal helpers
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        e.target.classList.remove('show');
        document.body.style.overflow = '';
    }
});

/**
 * Format ISO datetime string in user's clean local time
 */
function formatLocalDateTime(isoString) {
    if (!isoString) return 'N/A';
    try {
        const d = new Date(isoString);
        return d.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch {
        return isoString;
    }
}

/**
 * HTML Escaping utility
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

