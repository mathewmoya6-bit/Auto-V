(function() {
    if (window.autoV_Utils) return;
    
    window.autoV_Utils = {
        formatKES(amount) {
            return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES', minimumFractionDigits: 0 }).format(amount || 0);
        },
        
        formatDate(date) {
            return new Date(date).toLocaleDateString('en-KE', { year: 'numeric', month: 'short', day: 'numeric' });
        },
        
        formatDateTime(date) {
            return new Date(date).toLocaleString('en-KE');
        },
        
        showToast(msg, type = 'success') {
            const existing = document.querySelector('.toast');
            if (existing) existing.remove();
            const t = document.createElement('div');
            t.className = `toast toast-${type}`;
            t.textContent = msg;
            document.body.appendChild(t);
            setTimeout(() => t.remove(), 3000);
        },
        
        showLoading(show) {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) overlay.classList.toggle('active', show);
        },
        
        openModal(id) {
            document.getElementById(id).classList.add('active');
        },
        
        closeModal(id) {
            document.getElementById(id).classList.remove('active');
        },
        
        showConfirm(title, message, onConfirm) {
            document.getElementById('confirmTitle').textContent = title;
            document.getElementById('confirmMessage').textContent = message;
            document.getElementById('confirmDeleteBtn').onclick = function() {
                window.autoV_Utils.closeModal('confirmModal');
                if (onConfirm) onConfirm();
            };
            this.openModal('confirmModal');
        },
        
        getBadge(status) {
            const map = {
                pending: 'badge-pending',
                approved: 'badge-approved',
                rejected: 'badge-rejected',
                completed: 'badge-completed',
                active: 'badge-active',
                inactive: 'badge-inactive'
            };
            return map[status] || 'badge-pending';
        },
        
        renderSpinner() {
            return '<div class="spinner"></div>';
        },
        
        renderEmpty(message = 'No data found') {
            return `<tr><td colspan="10" class="empty-state">${message}</td></tr>`;
        }
    };
    
    console.log('✅ Utils loaded');
})();
