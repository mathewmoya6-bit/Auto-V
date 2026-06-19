(function() {
    if (window.autoV_Auth) return;
    
    const supabase = window.autoV.supabase;
    
    window.autoV_Auth = {
        currentUser: null,
        
        async checkAuth() {
            try {
                const { data: { user }, error } = await supabase.auth.getUser();
                if (error || !user) {
                    window.location.href = 'login.html';
                    return false;
                }
                this.currentUser = user;
                document.getElementById('adminEmail').textContent = user.email;
                return true;
            } catch (e) {
                console.error('Auth error:', e);
                return false;
            }
        },
        
        async requireAdmin() {
            if (!await this.checkAuth()) return false;
            const { data } = await supabase.from('user_profiles').select('role').eq('id', this.currentUser.id).maybeSingle();
            if (!data || data.role !== 'admin') {
                window.location.href = 'dashboard.html';
                return false;
            }
            return true;
        },
        
        getCurrentUser() { return this.currentUser; },
        
        async logout() {
            await supabase.auth.signOut();
            window.location.href = 'login.html';
        }
    };
    
    console.log('✅ Auth service loaded');
})();
