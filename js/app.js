(function() {
    if (window.autoV_AdminInitialized) return;
    window.autoV_AdminInitialized = true;
    
    function waitForDependencies(callback, retries = 20) {
        const required = ['autoV', 'autoV_API', 'autoV_Auth', 'autoV_Utils'];
        const allLoaded = required.every(r => window[r]);
        if (allLoaded) { callback(); return; }
        if (retries <= 0) { console.error('❌ Dependencies failed to load'); return; }
        setTimeout(() => waitForDependencies(callback, retries - 1), 300);
    }
    
    waitForDependencies(async function() {
        console.log('🚀 Admin dashboard initializing...');
        if (!await window.autoV_Auth.requireAdmin()) return;
        window.DashboardModule.init();
    });
})();
