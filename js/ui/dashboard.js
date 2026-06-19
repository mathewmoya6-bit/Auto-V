// ============================================================
// AUTO-V ADMIN DASHBOARD - Main Controller
// ============================================================

(function() {
    if (window.DashboardModule) return;
    
    const Utils = window.autoV_Utils;
    const Auth = window.autoV_Auth;
    
    window.DashboardModule = {
        currentTab: 'overview',
        refreshTimer: null,
        modules: {},
        
        init() {
            console.log('🚀 Initializing dashboard...');
            
            // Register all modules
            this.modules = {
                overview: window.OverviewModule,
                activities: window.ActivitiesModule,
                payments: window.PaymentsModule,
                fees: window.FeesModule,
                rates: window.RatesModule,
                users: window.UsersModule,
                requests: window.RequestsModule
            };
            
            // Setup tab switching
            this.setupTabs();
            
            // Load all tabs initially
            this.loadAllTabs();
            
            // Setup auto-refresh
            this.startAutoRefresh();
            
            // Setup logout
            document.getElementById('logoutBtn').addEventListener('click', () => Auth.logout());
            
            // Display admin email
            const user = Auth.getCurrentUser();
            if (user) {
                document.getElementById('adminEmail').textContent = user.email;
            }
        },
        
        setupTabs() {
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const tab = btn.dataset.tab;
                    this.switchTab(tab);
                });
            });
        },
        
        switchTab(tab) {
            this.currentTab = tab;
            
            // Update active tab button
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelector(`.tab-btn[data-tab="${tab}"]`)?.classList.add('active');
            
            // Update active content
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            const target = document.getElementById('tab-' + tab);
            if (target) target.classList.add('active');
            
            // Load the module
            if (this.modules[tab] && typeof this.modules[tab].load === 'function') {
                console.log(`📋 Loading ${tab} tab...`);
                this.modules[tab].load();
            }
        },
        
        async loadAllTabs() {
            console.log('📊 Loading all tabs...');
            Utils.showLoading(true);
            
            try {
                const loadPromises = Object.values(this.modules)
                    .filter(m => m && typeof m.load === 'function')
                    .map(m => m.load().catch(e => console.warn('Module load error:', e)));
                
                await Promise.all(loadPromises);
                console.log('✅ All tabs loaded successfully');
            } catch (e) {
                console.error('Error loading tabs:', e);
                Utils.showToast('Error loading dashboard data', 'error');
            } finally {
                Utils.showLoading(false);
            }
        },
        
        startAutoRefresh() {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
            this.refreshTimer = setInterval(() => {
                console.log('🔄 Auto-refreshing dashboard...');
                if (this.modules[this.currentTab] && typeof this.modules[this.currentTab].load === 'function') {
                    this.modules[this.currentTab].load();
                }
            }, 30000);
        },
        
        stopAutoRefresh() {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null;
            }
        },
        
        refreshCurrentTab() {
            if (this.modules[this.currentTab] && typeof this.modules[this.currentTab].load === 'function') {
                Utils.showToast('🔄 Refreshing...', 'warning');
                this.modules[this.currentTab].load();
            }
        }
    };
    
    console.log('✅ Dashboard module loaded');
})();
