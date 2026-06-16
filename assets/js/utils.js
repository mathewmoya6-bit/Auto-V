/* ============================================
   AUTO-V UTILITY FUNCTIONS
   Production Ready
   ============================================ */

const AUTOV = {
    // Format currency
    formatKES(amount) {
        return new Intl.NumberFormat('en-KE', {
            style: 'currency',
            currency: 'KES',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount || 0);
    },

    // Format date
    formatDate(date, format = 'short') {
        const d = new Date(date);
        if (format === 'short') return d.toLocaleDateString('en-KE');
        if (format === 'long') return d.toLocaleDateString('en-KE', { year: 'numeric', month: 'long', day: 'numeric' });
        if (format === 'datetime') return d.toLocaleString('en-KE');
        return d.toISOString().split('T')[0];
    },

    // Show toast notification
    toast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = 	oast toast-;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    // Debounce function
    debounce(func, wait = 300) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Generate random ID
    generateId(prefix = 'AUTO') {
        return ${prefix}--;
    },

    // Validate email
    isValidEmail(email) {
        return /^[^\s@]+@([^\s@.,]+\.)+[^\s@.,]{2,}$/.test(email);
    },

    // Validate phone (Kenyan)
    isValidPhone(phone) {
        return /^(07|01)\d{8}$/.test(phone);
    },

    // Download file
    downloadFile(content, filename, type = 'text/plain') {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    // Copy to clipboard
    copyToClipboard(text) {
        navigator.clipboard.writeText(text);
        this.toast('Copied to clipboard!', 'success');
    },

    // Get URL parameters
    getUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const result = {};
        for (const [key, value] of params) {
            result[key] = value;
        }
        return result;
    },

    // Print element
    printElement(elementId) {
        const content = document.getElementById(elementId);
        if (!content) return;
        const win = window.open('', '_blank');
        win.document.write(
            <html><head><title>AUTO-V Report</title>
            <style>body{font-family:Arial;padding:20px;} table{width:100%;border-collapse:collapse;} th,td{border:1px solid #ddd;padding:8px;}</style>
            </head><body></body></html>
        );
        win.document.close();
        win.print();
    },

    // Export table to CSV
    exportToCSV(tableId, filename = 'export.csv') {
        const table = document.getElementById(tableId);
        if (!table) return;
        let csv = [];
        const rows = table.querySelectorAll('tr');
        for (const row of rows) {
            const cells = row.querySelectorAll('th, td');
            csv.push(Array.from(cells).map(c => c.textContent.trim()).join(','));
        }
        this.downloadFile(csv.join('\n'), filename, 'text/csv');
    },

    // Chart colors
    chartColors: [
        '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ef4444',
        '#f59e0b', '#06b6d4', '#ec4899', '#14b8a6', '#f97316'
    ],

    // Get chart color by index
    getChartColor(index) {
        return this.chartColors[index % this.chartColors.length];
    },

    // Loading overlay
    showLoading(show) {
        let overlay = document.getElementById('loadingOverlay');
        if (show && !overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.style.cssText = 
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.8); z-index: 9999;
                display: flex; justify-content: center; align-items: center;
            ;
            overlay.innerHTML = '<div class="spinner"></div>';
            document.body.appendChild(overlay);
        } else if (!show && overlay) {
            overlay.remove();
        }
    },

    // Safe JSON parse
    safeJsonParse(str, fallback = null) {
        try { return JSON.parse(str); }
        catch (e) { return fallback; }
    },

    // Truncate text
    truncate(text, length = 50) {
        if (text.length <= length) return text;
        return text.substring(0, length) + '...';
    },

    // Get vehicle age
    getVehicleAge(year) {
        return new Date().getFullYear() - year;
    }
};

// Make available globally
window.AUTOV = AUTOV;

console.log('✅ AUTO-V utilities loaded');
