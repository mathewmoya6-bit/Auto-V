// js/error-handler.js
// =============================================================================
// AUTO-V Error Handler
// =============================================================================

class ErrorHandler {
    static handle(error, context = 'Unknown') {
        console.error(`❌ Error in ${context}:`, error);

        let message = error.message || 'An unexpected error occurred';

        // Network errors
        if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
            message = 'Network error - Cannot reach the server. Please check your connection.';
        }

        // CORS errors
        if (message.includes('CORS') || message.includes('cross-origin')) {
            message = 'CORS error - The server is not configured to accept requests from this domain.';
        }

        // Authentication errors
        if (message.includes('401')) {
            message = 'Authentication failed. Please log in again.';
        }

        if (message.includes('403')) {
            message = 'Access denied. You do not have permission to perform this action.';
        }

        if (message.includes('404')) {
            message = 'Resource not found. The requested endpoint does not exist.';
        }

        if (message.includes('429')) {
            message = 'Too many requests. Please try again later.';
        }

        if (message.includes('500')) {
            message = 'Server error. Please try again later.';
        }

        // Show toast notification
        ErrorHandler.showToast(message, 'error');

        return message;
    }

    static showToast(message, type = 'info', duration = 5000) {
        // Remove existing toast
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        // Create toast
        const div = document.createElement('div');
        div.className = `toast toast-${type}`;
        div.textContent = message;
        document.body.appendChild(div);

        // Auto-remove after duration
        setTimeout(() => {
            if (div.parentNode) div.remove();
        }, duration);
    }
}

// Expose globally
window.ErrorHandler = ErrorHandler;

// Add toast styles if not already present
if (!document.querySelector('#toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 9999;
            font-weight: 500;
            animation: toastSlideIn 0.3s ease;
            max-width: 380px;
            font-size: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .toast-success { background: #22c55e; color: #000; }
        .toast-error { background: #ef4444; color: #fff; }
        .toast-info { background: #3b82f6; color: #fff; }
        .toast-warning { background: #f59e0b; color: #000; }
        @keyframes toastSlideIn {
            from { opacity: 0; transform: translateX(80px); }
            to { opacity: 1; transform: translateX(0); }
        }
    `;
    document.head.appendChild(style);
}

console.log('✅ Error Handler initialized');
