// ── DOM Elements for Roles ───────────────────────────────────────────────────
const rolesSection = document.getElementById('roles-section');
const rolesTableBody = document.getElementById('roles-table-body');
const btnAddRole = document.getElementById('btn-add-role');
const roleModal = document.getElementById('role-modal');
const rolePermissionsModal = document.getElementById('role-permissions-modal');

// ── Load Roles ───────────────────────────────────────────────────────────────
async function loadRoles() {
  if (!rolesTableBody) return;
  rolesTableBody.innerHTML = '<tr><td colspan="4">Loading roles...</td></tr>';
  try {
    const data = await fetchAPI('/api/roles');
    if (!data.roles || data.roles.length === 0) {
      rolesTableBody.innerHTML = '<tr><td colspan="4">No roles found</td></tr>';
      return;
    }
    
    // Also update the User Modal select if it exists
    const userRoleSelect = document.getElementById('user-modal-role');
    if (userRoleSelect) {
      userRoleSelect.innerHTML = data.roles.map(r => `<option value="${r.name}">${r.name.toUpperCase()}</option>`).join('');
    }

    rolesTableBody.innerHTML = data.roles.map(role => {
      let actions = '';
      if (_canDo('users.manage_permissions')) {
        actions += `<button class="btn-icon-sm" title="Edit Permissions" onclick="openRolePermissionsModal('${role.name}')"><i class="fa-solid fa-shield-halved"></i></button>`;
        if (!role.is_system) {
          actions += `<button class="btn-icon-sm btn-icon-danger" title="Delete Role" onclick="deleteRole('${role.name}')"><i class="fa-solid fa-trash"></i></button>`;
        }
      }
      if (!actions) actions = '<span class="text-muted">—</span>';
      
      const typeBadge = role.is_system 
        ? '<span class="status-badge status-active">System Default</span>'
        : '<span class="status-badge status-inactive">Custom Role</span>';

      return `<tr>
        <td class="text-teal" style="font-weight: 600;">${role.name.toUpperCase()}</td>
        <td>${role.description || '<span class="text-muted">No description</span>'}</td>
        <td>${typeBadge}</td>
        <td style="text-align: right;">${actions}</td>
      </tr>`;
    }).join('');
  } catch (error) {
    rolesTableBody.innerHTML = '<tr><td colspan="4" class="text-danger">Failed to load roles.</td></tr>';
  }
}

// ── Role CRUD ────────────────────────────────────────────────────────────────
function _showRoleModal() { roleModal.classList.add('active'); }
function _hideRoleModal() { roleModal.classList.remove('active'); }

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
      // Update existing role description (not supported in UI right now, just prepared)
      await fetchAPI(`/api/roles/${originalName}`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ description: desc }) 
      });
      window.showToast('Role updated successfully', 'success');
    } else {
      // Create new role
      await fetchAPI('/api/roles', { 
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
    message: `Are you sure you want to delete role <strong>${name}</strong>?<br>This action cannot be undone.`,
    confirmText: 'DELETE', 
    cancelText: 'CANCEL', 
    variant: 'danger'
  });
  if (!confirmed) return;
  
  try {
    await fetchAPI(`/api/roles/${name}`, { method: 'DELETE' });
    window.showToast('Role deleted', 'success');
    loadRoles();
  } catch (error) {
    window.showToast('Failed to delete role: ' + error.message, 'error');
  }
}

// ── Role Permissions ─────────────────────────────────────────────────────────
function _showRolePermsModal() { rolePermissionsModal.classList.add('active'); }
function _hideRolePermsModal() { rolePermissionsModal.classList.remove('active'); }

async function openRolePermissionsModal(name) {
  document.getElementById('role-permissions-name').value = name;
  document.getElementById('role-permissions-title-name').textContent = name.toUpperCase();
  document.getElementById('role-permissions-error').classList.add('hidden');
  
  const grid = document.getElementById('role-permissions-grid');
  grid.innerHTML = '<p class="text-muted">Loading permissions...</p>';
  _showRolePermsModal();
  
  try {
    const data = await fetchAPI(`/api/roles/${name}/permissions`);
    const perms = data.permissions || {};
    
    // Use PERMISSION_GROUPS and PERMISSION_LABELS from user.js
    let html = '';
    for (const [group, keys] of Object.entries(PERMISSION_GROUPS)) {
      html += `<div class="perm-group"><div class="perm-group-title">${group}</div>`;
      for (const key of keys) {
        const isGranted = !!perms[key];
        html += `<div class="perm-row">
          <label class="toggle-switch">
            <input type="checkbox" data-role-perm-key="${key}" ${isGranted ? 'checked' : ''}>
            <span class="toggle-track"></span>
            <span>${PERMISSION_LABELS[key] || key}</span>
          </label>
        </div>`;
      }
      html += '</div>';
    }
    grid.innerHTML = html;
  } catch (error) {
    grid.innerHTML = '<p class="text-danger">Failed to load permissions.</p>';
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
    await fetchAPI(`/api/roles/${name}/permissions`, { 
      method: 'PUT', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ permissions }) 
    });
    window.showToast('Role permissions saved', 'success');
    _hideRolePermsModal();
  } catch (error) {
    errText.textContent = error.message;
    errEl.classList.remove('hidden');
  } finally {
    if (window.setButtonLoading) window.setButtonLoading(btn, false);
  }
}

// ── Event listeners ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (btnAddRole) btnAddRole.addEventListener('click', openCreateRoleModal);
  
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
  
  // Hook into section navigation to load roles
  const originalShowSection = window.showSection;
  if (originalShowSection) {
    window.showSection = function(sectionName) {
      originalShowSection(sectionName);
      if (sectionName === 'roles') loadRoles();
    };
  }
});
