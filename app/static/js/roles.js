// ── Roles Management ─────────────────────────────────────────────────────────

(function() {
  function _getCanDo(perm) {
    if (window._canDo) return window._canDo(perm);
    const u = window.currentUser;
    if (!u) return false;
    if (u.role === 'admin') return true;
    return !!(u.permissions && u.permissions[perm]);
  }

  const escapeHtml = window.escapeHtml || function(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  // ── DOM Elements for Roles ───────────────────────────────────────────────────
  const rolesTableBody = document.getElementById('roles-table-body');
  const btnAddRole = document.getElementById('btn-add-role');
  const roleModal = document.getElementById('role-modal');
  const rolePermissionsModal = document.getElementById('role-permissions-modal');

  // ── Load Roles ───────────────────────────────────────────────────────────────
  async function loadRoles() {
    const tableBody = document.getElementById('roles-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="4">Loading roles...</td></tr>';
    try {
      if (window.loadUserInfo && !window.currentUser) {
        await window.loadUserInfo();
      }

      const data = await window.fetchAPI('/api/roles');
      if (!data.roles || data.roles.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4">No roles found</td></tr>';
        return;
      }
      
      // Also update the User Modal select if it exists
      const userRoleSelect = document.getElementById('user-modal-role');
      if (userRoleSelect) {
        userRoleSelect.innerHTML = data.roles.map(r => `<option value="${escapeHtml(r.name)}">${escapeHtml(r.name.toUpperCase())}</option>`).join('');
      }

      tableBody.innerHTML = data.roles.map(role => {
        let actions = '';
        if (role.is_system) {
          actions = '<span class="text-muted"><i class="fa-solid fa-lock fa-fw"></i> System Protected</span>';
        } else if (_getCanDo('users.manage_permissions')) {
          actions += `<button class="btn-icon-sm" title="Edit Permissions" onclick="openRolePermissionsModal('${escapeHtml(role.name)}')"><i class="fa-solid fa-shield-halved"></i></button>`;
          actions += `<button class="btn-icon-sm btn-icon-danger" title="Delete Role" onclick="deleteRole('${escapeHtml(role.name)}')"><i class="fa-solid fa-trash"></i></button>`;
        }
        if (!actions) actions = '<span class="text-muted">—</span>';
        
        const typeBadge = role.is_system 
          ? '<span class="status-badge status-active">System Default</span>'
          : '<span class="status-badge status-inactive">Custom Role</span>';

        return `<tr>
          <td class="text-teal" style="font-weight: 600;">${escapeHtml(role.name.toUpperCase())}</td>
          <td>${escapeHtml(role.description) || '<span class="text-muted">No description</span>'}</td>
          <td>${typeBadge}</td>
          <td style="text-align: right;">${actions}</td>
        </tr>`;
      }).join('');
    } catch (error) {
      if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-danger">Failed to load roles: ' + escapeHtml(error.message) + '</td></tr>';
      }
    }
  }

  // ── Role CRUD ────────────────────────────────────────────────────────────────
  function _showRoleModal() { if (roleModal) roleModal.classList.add('active'); }
  function _hideRoleModal() { if (roleModal) roleModal.classList.remove('active'); }

  function openCreateRoleModal() {
    document.getElementById('role-modal-title').textContent = 'CREATE ROLE';
    document.getElementById('role-modal-original-name').value = '';
    const nameInput = document.getElementById('role-modal-name');
    nameInput.value = '';
    nameInput.disabled = false;
    document.getElementById('role-modal-description').value = '';
    document.getElementById('role-modal-error').classList.add('hidden');
    _showRoleModal();
  }

  async function saveRole() {
    const errEl = document.getElementById('role-modal-error');
    const errText = document.getElementById('role-modal-error-text');
    errEl.classList.add('hidden');
    
    const originalName = document.getElementById('role-modal-original-name').value;
    const name = document.getElementById('role-modal-name').value.trim();
    const desc = document.getElementById('role-modal-description').value.trim();
    
    if (!name) {
      errText.textContent = 'Role name is required.';
      errEl.classList.remove('hidden');
      return;
    }
    
    const btn = document.getElementById('btn-save-role-modal');
    if (window.setButtonLoading) window.setButtonLoading(btn, true, 'SAVING...');
    
    try {
      if (originalName) {
        await window.fetchAPI(`/api/roles/${originalName}`, { 
          method: 'PUT', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ description: desc }) 
        });
        window.showToast('Role updated successfully', 'success');
      } else {
        await window.fetchAPI('/api/roles', { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' }, 
          body: JSON.stringify({ name: name, description: desc }) 
        });
        window.showToast('Role created successfully', 'success');
      }
      _hideRoleModal();
      loadRoles();
    } catch (error) {
      errText.textContent = error.message;
      errEl.classList.remove('hidden');
    } finally {
      if (window.setButtonLoading) window.setButtonLoading(btn, false);
    }
  }

  async function deleteRole(name) {
    const confirmed = await window.showConfirm({
      title: 'DELETE ROLE', 
      message: `Are you sure you want to delete role <strong>${escapeHtml(name)}</strong>?<br>This action cannot be undone.`,
      confirmText: 'DELETE', 
      cancelText: 'CANCEL', 
      variant: 'danger'
    });
    if (!confirmed) return;
    
    try {
      await window.fetchAPI(`/api/roles/${name}`, { method: 'DELETE' });
      window.showToast('Role deleted successfully', 'success');
      loadRoles();
    } catch (error) {
      window.showToast('Failed to delete role: ' + error.message, 'error');
    }
  }

  // ── Role Permissions ─────────────────────────────────────────────────────────
  function _showRolePermsModal() { if (rolePermissionsModal) rolePermissionsModal.classList.add('active'); }
  function _hideRolePermsModal() { if (rolePermissionsModal) rolePermissionsModal.classList.remove('active'); }

  async function openRolePermissionsModal(name) {
    document.getElementById('role-permissions-name').value = name;
    document.getElementById('role-permissions-title-name').textContent = name.toUpperCase();
    document.getElementById('role-permissions-error').classList.add('hidden');
    
    const grid = document.getElementById('role-permissions-grid');
    grid.innerHTML = '<p class="text-muted">Loading permissions...</p>';
    _showRolePermsModal();
    
    try {
      const data = await window.fetchAPI(`/api/roles/${name}/permissions`);
      const perms = data.permissions || {};
      const isSystem = !!data.is_system;

      const saveBtn = document.getElementById('btn-save-role-permissions');
      if (saveBtn) {
        saveBtn.style.display = isSystem ? 'none' : 'inline-block';
      }

      if (isSystem) {
        const errEl = document.getElementById('role-permissions-error');
        const errText = document.getElementById('role-permissions-error-text');
        errText.textContent = 'System default role permissions are locked and cannot be modified.';
        errEl.classList.remove('hidden');
      }
      
      const permGroups = window.PERMISSION_GROUPS || {
        'Links': ['links.view','links.add','links.bulk_add','links.edit','links.delete','links.ping','links.export'],
        'Users': ['users.view','users.add','users.edit','users.delete','users.reset_password','users.manage_permissions'],
        'Config': ['config.view','config.edit_smtp','config.edit_jumpserver','config.edit_app'],
        'Logs': ['logs.view_system','logs.view_ping','logs.export'],
        'Notifications': ['notifications.view_own','notifications.edit_own','notifications.manage_all']
      };
      const permLabels = window.PERMISSION_LABELS || {
        'links.view': 'View links', 'links.add': 'Add links', 'links.bulk_add': 'Bulk add links', 'links.edit': 'Edit links',
        'links.delete': 'Delete links', 'links.ping': 'Manual ping', 'links.export': 'Export links',
        'users.view': 'View users', 'users.add': 'Add users', 'users.edit': 'Edit users',
        'users.delete': 'Delete users', 'users.reset_password': 'Reset passwords',
        'users.manage_permissions': 'Manage permissions',
        'config.view': 'View settings', 'config.edit_smtp': 'Edit SMTP',
        'config.edit_jumpserver': 'Edit jump server', 'config.edit_app': 'Edit app settings',
        'logs.view_system': 'View system logs', 'logs.view_ping': 'View ping logs', 'logs.export': 'Export logs',
        'notifications.view_own': 'View notifications', 'notifications.edit_own': 'Edit notifications',
        'notifications.manage_all': 'Manage all notifications'
      };

      let html = '';
      for (const [group, keys] of Object.entries(permGroups)) {
        html += `<div class="perm-group"><div class="perm-group-title">${escapeHtml(group)}</div>`;
        for (const key of keys) {
          const isGranted = !!perms[key];
          const disabledAttr = isSystem ? 'disabled' : '';
          html += `<div class="perm-row">
            <label class="toggle-switch ${isSystem ? 'toggle-disabled' : ''}">
              <input type="checkbox" data-role-perm-key="${escapeHtml(key)}" ${isGranted ? 'checked' : ''} ${disabledAttr}>
              <span class="toggle-track"></span>
              <span>${escapeHtml(permLabels[key] || key)}</span>
            </label>
          </div>`;
        }
        html += '</div>';
      }
      grid.innerHTML = html;
    } catch (error) {
      grid.innerHTML = '<p class="text-danger">Failed to load permissions: ' + escapeHtml(error.message) + '</p>';
    }
  }

  async function saveRolePermissions() {
    const name = document.getElementById('role-permissions-name').value;
    const errEl = document.getElementById('role-permissions-error');
    const errText = document.getElementById('role-permissions-error-text');
    errEl.classList.add('hidden');
    
    const permissions = {};
    document.querySelectorAll('#role-permissions-grid [data-role-perm-key]').forEach(input => {
      permissions[input.dataset.rolePermKey] = input.checked;
    });
    
    const btn = document.getElementById('btn-save-role-permissions');
    if (window.setButtonLoading) window.setButtonLoading(btn, true, 'SAVING...');
    
    try {
      await window.fetchAPI(`/api/roles/${name}/permissions`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ permissions }) 
      });
      window.showToast('Role permissions saved successfully', 'success');
      _hideRolePermsModal();
    } catch (error) {
      errText.textContent = error.message;
      errEl.classList.remove('hidden');
    } finally {
      if (window.setButtonLoading) window.setButtonLoading(btn, false);
    }
  }

  // ── Event listeners ───────────────────────────────────────────────────────────
  function attachRoleListeners() {
    const addRoleBtn = document.getElementById('btn-add-role');
    if (addRoleBtn) addRoleBtn.addEventListener('click', openCreateRoleModal);
    
    const btnCloseRM = document.getElementById('btn-close-role-modal');
    const btnCancelRM = document.getElementById('btn-cancel-role-modal');
    const btnSaveRM = document.getElementById('btn-save-role-modal');
    if (btnCloseRM) btnCloseRM.addEventListener('click', _hideRoleModal);
    if (btnCancelRM) btnCancelRM.addEventListener('click', _hideRoleModal);
    if (btnSaveRM) btnSaveRM.addEventListener('click', saveRole);
    
    const btnCloseRPM = document.getElementById('btn-close-role-permissions');
    const btnCancelRPM = document.getElementById('btn-cancel-role-permissions');
    const btnSaveRPM = document.getElementById('btn-save-role-permissions');
    if (btnCloseRPM) btnCloseRPM.addEventListener('click', _hideRolePermsModal);
    if (btnCancelRPM) btnCancelRPM.addEventListener('click', _hideRolePermsModal);
    if (btnSaveRPM) btnSaveRPM.addEventListener('click', saveRolePermissions);
    
    if (roleModal) roleModal.addEventListener('click', (e) => { if (e.target === roleModal) _hideRoleModal(); });
    if (rolePermissionsModal) rolePermissionsModal.addEventListener('click', (e) => { if (e.target === rolePermissionsModal) _hideRolePermsModal(); });
  }

  // Expose functions globally on window
  window.loadRoles = loadRoles;
  window.openCreateRoleModal = openCreateRoleModal;
  window.saveRole = saveRole;
  window.deleteRole = deleteRole;
  window.openRolePermissionsModal = openRolePermissionsModal;
  window.saveRolePermissions = saveRolePermissions;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachRoleListeners);
  } else {
    attachRoleListeners();
  }
})();
