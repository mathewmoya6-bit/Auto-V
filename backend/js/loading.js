// js/loading.js
// =============================================================================
// AUTO-V Loading Utilities
// =============================================================================

class LoadingManager {
    constructor() {
        this.overlays = {};
        this.defaultOptions = {
            text: 'Loading...',
            spinner: true,
            overlay: true,
        };
    }

    show(target, options = {}) {
        const opts = { ...this.defaultOptions, ...options };
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        
        if (!element) {
            console.warn('Loading target not found:', target);
            return;
        }

        // Create loading overlay
        const id = `loading-${Date.now()}`;
        const overlay = document.createElement('div');
        overlay.id = id;
        overlay.className = 'loading-overlay';
        overlay.style.cssText = `
            position: absolute;
            inset: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            border-radius: inherit;
        `;

        if (opts.spinner) {
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            spinner.style.cssText = `
                width: 40px;
                height: 40px;
                border: 3px solid rgba(255,255,255,0.1);
                border-top-color: #eab308;
                border-radius: 50%;
                animation: loadingSpin 0.6s linear infinite;
            `;
            overlay.appendChild(spinner);
        }

        if (opts.text) {
            const text = document.createElement('p');
            text.textContent = opts.text;
            text.style.cssText = `
                color: #fff;
                margin-top: 12px;
                font-size: 14px;
                font-weight: 500;
            `;
            overlay.appendChild(text);
        }

        // Add position relative if needed
        if (getComputedStyle(element).position === 'static') {
            element.style.position = 'relative';
        }

        element.appendChild(overlay);
        this.overlays[id] = { element, overlay };

        return id;
    }

    hide(id) {
        if (id && this.overlays[id]) {
            const { overlay, element } = this.overlays[id];
            if (overlay.parentNode) {
                overlay.remove();
            }
            delete this.overlays[id];
        }
    }

    hideAll() {
        Object.keys(this.overlays).forEach(id => this.hide(id));
    }

    // Simple button loading state
    setButtonLoading(button, text = 'Loading...') {
        if (!button) return;
        const originalText = button.textContent;
        button.disabled = true;
        button.dataset.originalText = originalText;
        button.innerHTML = `<span class="loading-spinner-small"></span> ${text}`;
        
        // Add spinner style if not exists
        if (!document.querySelector('#loading-spinner-styles')) {
            const style = document.createElement('style');
            style.id = 'loading-spinner-styles';
            style.textContent = `
                .loading-spinner-small {
                    display: inline-block;
                    width: 14px;
                    height: 14px;
                    border: 2px solid rgba(255,255,255,0.2);
                    border-top-color: #fff;
                    border-radius: 50%;
                    animation: loadingSpin 0.6s linear infinite;
                    margin-right: 8px;
                    vertical-align: middle;
                }
                @keyframes loadingSpin {
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    resetButton(button) {
        if (!button) return;
        button.disabled = false;
        button.textContent = button.dataset.originalText || button.textContent;
    }
}

// Create global instance
const Loading = new LoadingManager();

console.log('✅ Loading utilities initialized');
