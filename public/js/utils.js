// ============================================================
// AUTO-V UTILITY FUNCTIONS
// ============================================================

/**
 * Format currency in Kenyan Shillings
 */
function formatCurrency(amount) {
    if (amount === undefined || amount === null || isNaN(amount)) return '0.00';
    return Number(amount).toLocaleString('en-KE', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatCurrencyKES(amount) {
    return `KES ${formatCurrency(amount)}`;
}

/**
 * Format date
 */
function formatDate(date) {
    if (!date) return '—';
    return new Date(date).toLocaleDateString('en-KE', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
}

function formatDateTime(date) {
    if (!date) return '—';
    return new Date(date).toLocaleString('en-KE', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatTimeAgo(date) {
    if (!date) return '—';
    const now = new Date();
    const diff = now - new Date(date);
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return formatDate(date);
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    return Number(num || 0).toLocaleString('en-KE');
}

/**
 * Truncate string
 */
function truncateString(str, len = 20) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

/**
 * Get status color
 */
function getStatusColor(status) {
    const colors = {
        'pending': '#f59e0b',
        'processing': '#3b82f6',
        'completed': '#22c55e',
        'failed': '#ef4444',
        'cancelled': '#64748b',
        'active': '#22c55e',
        'inactive': '#64748b',
        'paid': '#8b5cf6',
        'approved': '#22c55e',
        'verified': '#22c55e'
    };
    return colors[status] || '#94a3b8';
}

/**
 * Get service icon
 */
function getServiceIcon(service) {
    const icons = {
        'instant': '💡',
        'valuation': '💰',
        'inspection': '🔍',
        'assessment': '⚠️',
        'mileage': '📏',
        'fleet': '🚛',
        'verification': '✅'
    };
    return icons[service] || '📄';
}

/**
 * Get service name
 */
function getServiceName(service) {
    const names = {
        'instant': 'Instant Value Check',
        'valuation': 'Valuation',
        'inspection': 'Inspection',
        'assessment': 'Assessment',
        'mileage': 'Mileage Rate',
        'fleet': 'Fleet Management',
        'verification': 'Document Verification'
    };
    return names[service] || service;
}

/**
 * Get status badge class
 */
function getStatusBadge(status) {
    const map = {
        'completed': 'badge-completed',
        'paid': 'badge-paid',
        'pending': 'badge-pending',
        'processing': 'badge-processing',
        'failed': 'badge-failed',
        'cancelled': 'badge-cancelled',
        'active': 'badge-active',
        'inactive': 'badge-inactive',
        'verified': 'badge-success'
    };
    return map[status] || 'badge-pending';
}

/**
 * Debounce function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

/**
 * Throttle function
 */
function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Download CSV
 */
function downloadCSV(data, filename) {
    const rows = data.map(row => row.join(','));
    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Get vehicle icon by body type
 */
function getVehicleIcon(bodyType) {
    const icons = {
        'Sedan': '🚗',
        'SUV': '🚙',
        'Pickup': '🛻',
        'Van': '🚐',
        'Hatchback': '🚗',
        'Coupe': '🏎️',
        'Convertible': '🚗',
        'Wagon': '🚗',
        'Standard': '🏍️',
        'Sport': '🏍️',
        'Cruiser': '🏍️',
        'Passenger': '🛺',
        'Cargo': '🛺'
    };
    return icons[bodyType] || '🚗';
}

/**
 * Generate random ID
 */
function generateId(prefix = '') {
    const random = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `${prefix}${Date.now().toString(36)}${random}`;
}

/**
 * Validate email
 */
function isValidEmail(email) {
    return /^[^\s@]+@([^\s@.,]+\.)+[^\s@.,]{2,}$/.test(email);
}

/**
 * Validate phone number
 */
function isValidPhone(phone) {
    return /^[0-9]{10,12}$/.test(phone);
}

/**
 * Get query parameter from URL
 */
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

/**
 * Generate random avatar color
 */
function getAvatarColor(email) {
    let hash = 0;
    for (let i = 0; i < email.length; i++) {
        hash = email.charCodeAt(i) + ((hash << 5) - hash);
    }
    const colors = ['#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6'];
    return colors[Math.abs(hash) % colors.length];
}

/**
 * Get initials from name
 */
function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(' ');
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

// Export utilities
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatCurrency,
        formatCurrencyKES,
        formatDate,
        formatDateTime,
        formatTimeAgo,
        formatNumber,
        truncateString,
        getStatusColor,
        getServiceIcon,
        getServiceName,
        getStatusBadge,
        debounce,
        throttle,
        downloadCSV,
        getVehicleIcon,
        generateId,
        isValidEmail,
        isValidPhone,
        getQueryParam,
        getAvatarColor,
        getInitials
    };
}
