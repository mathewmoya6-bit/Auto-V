// ============================================================
// USERS UI Module
// ============================================================

(function() {
    if (window.UsersModule) return;
    
    const API = window.autoV_API;
    const Utils = window.autoV_Utils;
    
    window.UsersModule = {
        currentPage: 1,
        pageSize: 50,
        
        async load(page = 1) {
            this.currentPage = page;
            console.log('👥 Loading users...');
            const tbody = document.getElementById('usersBody');
            tbody.innerHTML = Utils.renderSpinner();
            
            try {
                const offset = (page - 1) * this.pageSize;
                const { data, error } = await API.getUsers(this.pageSize, offset);
                
                if (error) {
                    tbody.innerHTML = Utils.renderEmpty('❌ ' + error.message);
                    return;
                }
                
                if (!data || data.length === 0) {
                    tbody.innerHTML = Utils.renderEmpty('No users found');
                    return;
                }
                
                tbody.innerHTML = data.map(u => `
                    <tr>
                        <td>${u.email || '-'}</td>
                        <td>${u.full_name || '-'}</td>
                        <td>${u.phone || '-'}</td>
                        <td>
                            <span class="badge ${u.user_type === 'corporate' ? 'badge-approved' : 'badge-pending'}">
                                ${u.user_type || 'individual'}
                            </span>
                        </td>
                        <td>${Utils.formatDate(u.created_at)}</td>
                        <td>
                            <button class="btn btn-warning btn-sm" onclick="UsersModule.editUser('${u.id}')">✏️</button>
                            <button class="btn btn-danger btn-sm" onclick="UsersModule.deleteUser('${u.id}')">🗑️</button>
                        </td>
                    </tr>
                `).join('');
                
                // Setup search
                const searchInput = document.getElementById('userSearch');
                if (searchInput) {
                    searchInput.oninput = function() {
                        const s = this.value.toLowerCase();
                        document.querySelectorAll('#usersBody tr').forEach(row => {
                            row.style.display = row.textContent.toLowerCase().includes(s) ? '' : 'none';
                        });
                    };
                }
                
            } catch (e) {
                console.error('Users error:', e);
                tbody.innerHTML = Utils.renderEmpty('Error loading users');
                Utils.showToast('Error loading users', 'error');
            }
        },
        
        async editUser(id) {
            Utils.showLoading(true);
            try {
                const { data, error } = await API.getUser(id);
                if (error) throw error;
                
                document.getElementById('userFullName').value = data.full_name || '';
                document.getElementById('userPhone').value = data.phone || '';
                document.getElementById('userEditId').value = data.id;
                
                Utils.openModal('userModal');
            } catch (e) {
                Utils.showToast('Error loading user', 'error');
            } finally {
                Utils.showLoading(false);
            }
        },
        
        async deleteUser(id) {
            Utils.showConfirm('Delete User', 'Delete this user permanently?', async () => {
                Utils.showLoading(true);
                try {
                    const { error } = await API.deleteUser(id);
                    if (error) throw error;
                    
                    Utils.showToast('✅ User deleted');
                    await this.load(this.currentPage);
                    
                    if (window.OverviewModule && typeof window.OverviewModule.load === 'function') {
                        window.OverviewModule.load();
                    }
                } catch (e) {
                    Utils.showToast('Error deleting user: ' + e.message, 'error');
                } finally {
                    Utils.showLoading(false);
                }
            });
        },
        
        async saveUser() {
            const id = document.getElementById('userEditId').value;
            const fullName = document.getElementById('userFullName').value.trim();
            const phone = document.getElementById('userPhone').value.trim();
            
            if (!fullName) {
                Utils.showToast('Full name is required', 'warning');
                return;
            }
            
            Utils.showLoading(true);
            try {
                const { error } = await API.updateUser(id, {
                    full_name: fullName,
                    phone: phone
                });
                
                if (error) throw error;
                
                Utils.showToast('✅ User updated');
                Utils.closeModal('userModal');
                await this.load(this.currentPage);
            } catch (e) {
                Utils.showToast('Error updating user: ' + e.message, 'error');
            } finally {
                Utils.showLoading(false);
            }
        }
    };
    
    // Setup user form submit
    document.addEventListener('DOMContentLoaded', function() {
        document.getElementById('userForm')?.addEventListener('submit', function(e) {
            e.preventDefault();
            window.UsersModule?.saveUser();
        });
    });
    
    console.log('✅ Users module loaded');
})();
