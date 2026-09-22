// ── User & Auth System ─────────────────────────────────────────────────────────

// ── DOM Elements ──────────────────────────────────────────────────────────────
const userMenuBtn = document.getElementById('user-menu-btn');
const userDropdown = document.getElementById('user-dropdown');
const userName = document.getElementById('user-name');
const userRole = document.getElementById('user-role');
const logoutBtn = document.getElementById('logout-btn');
const changePasswordLink = document.getElementById('change-password-link');
const changePasswordModal = document.getElementById('change-password-modal');
const btnCloseChangePassword = document.getElementById('btn-close-change-password');
const btnCancelChangePassword = document.getElementById('btn-cancel-change-password');
const btnSaveChangePassword = document.getElementById('btn-save-change-password');
const changePasswordForm = document.getElementById('change-password-form');
const currentPasswordInput = document.getElementById('current-password');
const newPasswordInput = document.getElementById('new-password');
const confirmPasswordInput = document.getElementById('confirm-password');
const changePasswordError = document.getElementById('change-password-error');
const changePasswordErrorText = document.getElementById('change-password-error-text');
const navItems = document.querySelectorAll('.nav-item[data-section]');
const dashboardSection = document.getElementById('dashboard-section');
const logsSection = document.getElementById('logs-section');
const usersSection = document.getElementById('users-section');
const btnRefreshLogs = document.getElementById('btn-refresh-logs');
const logsTableBody = document.getElementById('logs-table-body');
const usersTableBody = document.getElementById('users-table-body');

let forcePasswordChangeRequired = false;
let currentUser = null;
let userInfoPromise = null;

// ── Permission labels ─────────────────────────────────────────────────────────
const PERMISSION_LABELS = {
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
const PERMISSION_GROUPS = {
  'Links': ['links.view','links.add','links.bulk_add','links.edit','links.delete','links.ping','links.export'],
  'Users': ['users.view','users.add','users.edit','users.delete','users.reset_password','users.manage_permissions'],
  'Config': ['config.view','config.edit_smtp','config.edit_jumpserver','config.edit_app'],
  'Logs': ['logs.view_system','logs.view_ping','logs.export'],
  'Notifications': ['notifications.view_own','notifications.edit_own','notifications.manage_all']
};

window.PERMISSION_LABELS = PERMISSION_LABELS;
window.PERMISSION_GROUPS = PERMISSION_GROUPS;

// ── Section navigation ────────────────────────────────────────────────────────
function showSection(sectionName) {
  const sectionMap = { 
    dashboard: dashboardSection, 
    logs: logsSection, 
    users: usersSection,
    roles: document.getElementById('roles-section')
  };
  Object.entries(sectionMap).forEach(([key, section]) => {
    if (section) section.classList.toggle('hidden', key !== sectionName);
  });
  navItems.forEach(item => item.classList.toggle('active', item.dataset.section === sectionName));
}

// ── Change Password ───────────────────────────────────────────────────────────
function showChangePasswordModal(required = false) {
  if (!changePasswordModal) return;
  forcePasswordChangeRequired = required;
  changePasswordModal.classList.remove('hidden');
  changePasswordModal.classList.add('active');
  btnCloseChangePassword?.classList.toggle('hidden', required);
  btnCancelChangePassword?.classList.toggle('hidden', required);
  clearChangePasswordError();
  currentPasswordInput?.focus();
}
function hideChangePasswordModal() {
  if (forcePasswordChangeRequired) return;
  if (!changePasswordModal) return;
  changePasswordModal.classList.remove('active');
  changePasswordModal.classList.add('hidden');
}
function clearChangePasswordError() {
  if (changePasswordError) { changePasswordError.classList.add('hidden'); changePasswordErrorText.textContent = ''; }
}
function showChangePasswordError(message) {
  if (changePasswordError) { changePasswordErrorText.textContent = message; changePasswordError.classList.remove('hidden'); }
  if (window.showToast) window.showToast(message, 'error');
}
async function handleChangePassword(event) {
  if (event) event.preventDefault();
  clearChangePasswordError();
  const cur = currentPasswordInput?.value || '';
  const np = newPasswordInput?.value || '';
  const cp = confirmPasswordInput?.value || '';
  if (!np || np.length < 8) { showChangePasswordError('New password must be at least 8 characters.'); return; }
  if (np !== cp) { showChangePasswordError('New password and confirmation do not match.'); return; }
  if (!forcePasswordChangeRequired && !cur) { showChangePasswordError('Current password is required.'); return; }
  if (window.setButtonLoading) window.setButtonLoading(btnSaveChangePassword, true, 'UPDATING...');
  try {
    await window.fetchAPI('/api/auth/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: cur, new_password: np, confirm_password: cp }) });
    if (window.showToast) window.showToast('Password updated successfully.', 'success');
    forcePasswordChangeRequired = false;
    hideChangePasswordModal();
  } catch (error) { showChangePasswordError(error.message); }
  finally { if (window.setButtonLoading) window.setButtonLoading(btnSaveChangePassword, false); }
}

// ── Load user info ────────────────────────────────────────────────────────────
async function loadUserInfo() {
  if (currentUser) {
    window.currentUser = currentUser;
    return currentUser;
  }
  if (!userInfoPromise) {
    userInfoPromise = (async () => {
      try {
        const data = await window.fetchAPI('/api/auth/me');
        currentUser = data;
        window.currentUser = data;
        if (userName) userName.textContent = currentUser.full_name || currentUser.username;
        if (userRole) userRole.textContent = currentUser.role ? currentUser.role.toUpperCase() : 'ADMINISTRATOR';
        if (currentUser.force_password_change) { showChangePasswordModal(true); showSection('dashboard'); }
        return currentUser;
      } catch (error) {
        console.error('Failed to load user info', error);
        if (userName) userName.textContent = 'Unknown User';
        if (userRole) userRole.textContent = 'User';
        return null;
      } finally {
        userInfoPromise = null;
      }
    })();
  }
  return userInfoPromise;
}

// ── System Logs ───────────────────────────────────────────────────────────────
async function loadSystemLogs() {
  if (!logsTableBody) return;
  logsTableBody.innerHTML = '<tr><td colspan="6">Loading logs...</td></tr>';
  try {
    const data = await window.fetchAPI('/api/logs/system?per_page=50');
    if (!data.logs || data.logs.length === 0) { logsTableBody.innerHTML = '<tr><td colspan="6">No logs available</td></tr>'; return; }
    const esc = window.escapeHtml || ((s) => s);
    logsTableBody.innerHTML = data.logs.map(log => `
      <tr>
        <td>${new Date(log.timestamp).toLocaleString()}</td>
        <td>${esc(log.category || '')}</td>
        <td>${esc(log.event || '')}</td>
        <td>${esc(log.actor || '')}</td>
        <td>${esc(log.target || '')}</td>
        <td>${esc(log.detail || '')}</td>
      </tr>
    `).join('');
  } catch (error) { logsTableBody.innerHTML = '<tr><td colspan="6">Unable to load logs.</td></tr>'; }
}

// ── Users Table ───────────────────────────────────────────────────────────────
function _roleBadgeClass(role) {
  if (role === 'admin') return 'role-admin';
  return 'role-viewer';
}
function _statusBadge(status) {
  if (status === 'Active') return '<span class="status-badge status-active">Active</span>';
  if (status === 'Locked') return '<span class="status-badge status-locked">Locked</span>';
  return '<span class="status-badge status-inactive">Inactive</span>';
}
function _canDo(perm) {
  if (!currentUser) return false;
  if (currentUser.role === 'admin') return true;
  return !!(currentUser.permissions && currentUser.permissions[perm]);
}

let allUsersList = [];

function renderUsersTable() {
  if (!usersTableBody) return;
  const esc = window.escapeHtml || ((s) => s);
  const searchInput = document.getElementById('users-search-input');
  const roleFilter = document.getElementById('users-role-filter');
  const statusFilter = document.getElementById('users-status-filter');
  const countBadge = document.getElementById('users-count-badge');

  const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
  const selectedRole = roleFilter ? roleFilter.value : 'ALL';
  const selectedStatus = statusFilter ? statusFilter.value : 'ALL';

  const filtered = allUsersList.filter(user => {
    if (selectedRole !== 'ALL' && (user.role || '').toLowerCase() !== selectedRole.toLowerCase()) {
      return false;
    }
    if (selectedStatus !== 'ALL' && user.status !== selectedStatus) {
      return false;
    }
    if (query) {
      const matchName = (user.full_name || '').toLowerCase().includes(query);
      const matchUser = (user.username || '').toLowerCase().includes(query);
      const matchEmail = (user.email || '').toLowerCase().includes(query);
      const matchRole = (user.role || '').toLowerCase().includes(query);
      if (!matchName && !matchUser && !matchEmail && !matchRole) {
        return false;
      }
    }
    return true;
  });

  if (countBadge) {
    if (filtered.length !== allUsersList.length) {
      countBadge.textContent = `${filtered.length} OF ${allUsersList.length} TOTAL`;
    } else {
      countBadge.textContent = `${allUsersList.length} TOTAL`;
    }
  }

  if (filtered.length === 0) {
    usersTableBody.innerHTML = '<tr><td colspan="7" class="text-muted" style="text-align: center; padding: 24px;">No matching users found</td></tr>';
    return;
  }

  usersTableBody.innerHTML = filtered.map(user => {
    let actions = '';
    if (_canDo('users.edit'))
      actions += `<button class="btn-icon-sm" title="Edit" onclick="openEditUserModal(${user.id})"><i class="fa-solid fa-pen"></i></button>`;
    if (_canDo('users.reset_password'))
      actions += `<button class="btn-icon-sm" title="Reset Password" onclick="openResetPasswordModal(${user.id}, '${esc(user.username)}')"><i class="fa-solid fa-key"></i></button>`;

    if (user.is_locked && _canDo('users.edit'))
      actions += `<button class="btn-icon-sm btn-icon-warning" title="Unlock" onclick="unlockUser(${user.id})"><i class="fa-solid fa-lock-open"></i></button>`;
    if (_canDo('users.delete') && (!currentUser || user.id !== currentUser.id))
      actions += `<button class="btn-icon-sm btn-icon-danger" title="Delete" onclick="deleteUser(${user.id}, '${esc(user.username)}')"><i class="fa-solid fa-trash"></i></button>`;
    if (!actions) actions = '<span class="text-muted">—</span>';
    return `<tr>
      <td>${esc(user.full_name)}</td>
      <td class="text-mono text-secondary">${esc(user.username)}</td>
      <td>${esc(user.email)}</td>
      <td><span class="role-badge ${_roleBadgeClass(user.role)}">${esc((user.role || '').toUpperCase())}</span></td>
      <td>${_statusBadge(user.status)}</td>
      <td>${user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '<span class="text-muted">Never</span>'}</td>
      <td style="text-align: right;">${actions}</td>
    </tr>`;
  }).join('');
}

async function loadUsers() {
  if (!usersTableBody) return;
  usersTableBody.innerHTML = '<tr><td colspan="7">Loading users...</td></tr>';
  try {
    if (!currentUser) {
      await loadUserInfo();
    }
    const [userData, rolesData] = await Promise.all([
      window.fetchAPI('/api/users'),
      window.fetchAPI('/api/roles').catch(() => ({ roles: [] }))
    ]);

    allUsersList = userData.users || [];

    // Populate role filter dropdown if present
    const roleFilter = document.getElementById('users-role-filter');
    if (roleFilter && rolesData.roles && rolesData.roles.length > 0) {
      const currentVal = roleFilter.value;
      const esc = window.escapeHtml || ((s) => s);
      let optionsHtml = '<option value="ALL">All Roles</option>';
      rolesData.roles.forEach(r => {
        optionsHtml += `<option value="${esc(r.name)}" ${currentVal === r.name ? 'selected' : ''}>${esc(r.name.toUpperCase())}</option>`;
      });
      roleFilter.innerHTML = optionsHtml;
    }

    renderUsersTable();
  } catch (error) {
    const esc = window.escapeHtml || ((s) => s);
    usersTableBody.innerHTML = '<tr><td colspan="7">Unable to load users: ' + esc(error.message) + '</td></tr>';
  }
}

// ── User Modal (Create / Edit) ────────────────────────────────────────────────
function _showUserModal() { document.getElementById('user-modal').classList.add('active'); }
function _hideUserModal() { document.getElementById('user-modal').classList.remove('active'); }

async function _populateRolesSelect() {
  const select = document.getElementById('user-modal-role');
  try {
    const data = await window.fetchAPI('/api/roles');
    const esc = window.escapeHtml || ((s) => s);
    if (data.roles) {
      select.innerHTML = data.roles.map(r => `<option value="${esc(r.name)}">${esc(r.name.toUpperCase())}</option>`).join('');
    }
  } catch (error) {
    select.innerHTML = '<option value="">Error loading roles</option>';
  }
}

async function openCreateUserModal() {
  await _populateRolesSelect();
  document.getElementById('user-modal-title').textContent = 'CREATE USER';
  document.getElementById('user-modal-id').value = '';
  document.getElementById('user-modal-fullname').value = '';
  document.getElementById('user-modal-username').value = '';
  document.getElementById('user-modal-username').disabled = false;
  document.getElementById('user-modal-email').value = '';
  document.getElementById('user-modal-role').value = 'admin';
  document.getElementById('user-modal-password').value = '';
  document.getElementById('user-modal-password').placeholder = 'Enter password (min 8 chars)';
  const pwLabel = document.getElementById('user-modal-password-label');
  if (pwLabel) pwLabel.textContent = 'Password';
  const pwHelper = document.getElementById('user-modal-password-helper');
  if (pwHelper) pwHelper.textContent = 'Default: ChangeMe123! if blank';
  document.getElementById('user-modal-active').checked = true;
  document.getElementById('user-modal-force-pw').checked = true;
  document.getElementById('user-modal-error').classList.add('hidden');
  _showUserModal();
}

async function openEditUserModal(userId) {
  try {
    const [userData, _] = await Promise.all([
      window.fetchAPI(`/api/users/${userId}`),
      _populateRolesSelect()
    ]);
    const u = userData.user;
    document.getElementById('user-modal-title').textContent = 'EDIT USER';
    document.getElementById('user-modal-id').value = u.id;
    document.getElementById('user-modal-fullname').value = u.full_name;
    document.getElementById('user-modal-username').value = u.username;
    document.getElementById('user-modal-username').disabled = true;
    document.getElementById('user-modal-email').value = u.email;
    document.getElementById('user-modal-role').value = u.role;
    document.getElementById('user-modal-password').value = '';
    document.getElementById('user-modal-password').placeholder = 'Leave blank to keep existing password';
    const pwLabel = document.getElementById('user-modal-password-label');
    if (pwLabel) pwLabel.textContent = 'New Password (optional)';
    const pwHelper = document.getElementById('user-modal-password-helper');
    if (pwHelper) pwHelper.textContent = 'Leave blank to keep existing password';
    document.getElementById('user-modal-active').checked = u.is_active;
    document.getElementById('user-modal-force-pw').checked = u.force_password_change;
    document.getElementById('user-modal-error').classList.add('hidden');
    _showUserModal();
  } catch (error) { window.showToast('Failed to load user: ' + error.message, 'error'); }
}

async function saveUser() {
  const errEl = document.getElementById('user-modal-error');
  const errText = document.getElementById('user-modal-error-text');
  errEl.classList.add('hidden');
  const id = document.getElementById('user-modal-id').value;
  const isEdit = !!id;
  const pw = document.getElementById('user-modal-password').value.trim();

  if (pw && pw.length < 8) {
    errText.textContent = 'Password must be at least 8 characters.';
    errEl.classList.remove('hidden');
    return;
  }

  const payload = {
    full_name: document.getElementById('user-modal-fullname').value.trim(),
    email: document.getElementById('user-modal-email').value.trim(),
    role: document.getElementById('user-modal-role').value,
    is_active: document.getElementById('user-modal-active').checked,
    force_password_change: document.getElementById('user-modal-force-pw').checked
  };

  if (pw) {
    payload.password = pw;
  }

  if (!isEdit) {
    payload.username = document.getElementById('user-modal-username').value.trim();
  }

  if (!payload.full_name || !payload.email || (!isEdit && !payload.username)) {
    errText.textContent = 'Please fill in all required fields.';
    errEl.classList.remove('hidden');
    return;
  }

  const btn = document.getElementById('btn-save-user-modal');
  if (window.setButtonLoading) window.setButtonLoading(btn, true, 'SAVING...');
  try {
    if (isEdit) {
      await window.fetchAPI(`/api/users/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      window.showToast('User updated successfully', 'success');
    } else {
      await window.fetchAPI('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      window.showToast('User created successfully', 'success');
    }
    _hideUserModal();
    loadUsers();
  } catch (error) {
    errText.textContent = error.message;
    errEl.classList.remove('hidden');
  } finally {
    if (window.setButtonLoading) window.setButtonLoading(btn, false);
  }
}

async function deleteUser(userId, username) {
  const esc = window.escapeHtml || ((s) => s);
  const confirmed = await window.showConfirm({
    title: 'DELETE USER',
    message: `Are you sure you want to delete user <strong>${esc(username)}</strong>?<br>This action cannot be undone.`,
    confirmText: 'DELETE',
    cancelText: 'CANCEL',
    variant: 'danger'
  });
  if (!confirmed) return;
  try {
    await window.fetchAPI(`/api/users/${userId}`, { method: 'DELETE' });
    window.showToast('User deleted successfully', 'success');
    loadUsers();
  } catch (error) {
    window.showToast('Failed to delete user: ' + error.message, 'error');
  }
}

async function unlockUser(userId) {
  const confirmed = await window.showConfirm({
    title: 'UNLOCK USER',
    message: 'Unlock this user account and reset the failed login counter?',
    confirmText: 'UNLOCK',
    cancelText: 'CANCEL',
    variant: 'warning'
  });
  if (!confirmed) return;
  try {
    await window.fetchAPI(`/api/users/${userId}/unlock`, { method: 'POST' });
    window.showToast('User unlocked successfully', 'success');
    loadUsers();
  } catch (error) {
    window.showToast('Failed to unlock user: ' + error.message, 'error');
  }
}

// ── Reset Password Modal ──────────────────────────────────────────────────────
function _showResetPwModal() { document.getElementById('reset-password-modal').classList.add('active'); }
function _hideResetPwModal() { document.getElementById('reset-password-modal').classList.remove('active'); }

function openResetPasswordModal(userId, username) {
  document.getElementById('reset-pw-user-id').value = userId;
  document.getElementById('reset-pw-username').textContent = username;
  document.getElementById('reset-pw-new').value = '';
  document.getElementById('reset-pw-confirm').value = '';
  document.getElementById('reset-pw-force').checked = true;
  document.getElementById('reset-pw-error').classList.add('hidden');
  _showResetPwModal();
}

async function saveResetPassword() {
  const errEl = document.getElementById('reset-pw-error');
  const errText = document.getElementById('reset-pw-error-text');
  errEl.classList.add('hidden');
  const userId = document.getElementById('reset-pw-user-id').value;
  const np = document.getElementById('reset-pw-new').value.trim();
  const cp = document.getElementById('reset-pw-confirm').value.trim();
  const force = document.getElementById('reset-pw-force').checked;
  if (!np || np.length < 8) { errText.textContent = 'Password must be at least 8 characters.'; errEl.classList.remove('hidden'); return; }
  if (np !== cp) { errText.textContent = 'Passwords do not match.'; errEl.classList.remove('hidden'); return; }
  const btn = document.getElementById('btn-save-reset-pw');
  if (window.setButtonLoading) window.setButtonLoading(btn, true, 'RESETTING...');
  try {
    await window.fetchAPI(`/api/users/${userId}/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: np, confirm_password: cp, force_password_change: force }) });
    window.showToast('Password reset successfully', 'success');
    _hideResetPwModal();
    loadUsers();
  } catch (error) {
    errText.textContent = error.message;
    errEl.classList.remove('hidden');
  } finally {
    if (window.setButtonLoading) window.setButtonLoading(btn, false);
  }
}

// ── Navigation ────────────────────────────────────────────────────────────────
function handleNavClick(event) {
  const section = event.currentTarget.dataset.section;
  if (!section) return;
  showSection(section);
  if (section === 'logs') loadSystemLogs();
  else if (section === 'users') loadUsers();
  else if (section === 'roles' && window.loadRoles) window.loadRoles();
}
function toggleUserDropdown() { userDropdown.classList.toggle('active'); }
async function handleLogout(event) {
  event.preventDefault();
  try { await window.fetchAPI('/api/auth/logout', { method: 'POST' }); } catch (error) {}
  window.location.href = window.APP_PREFIX + '/login';
}

// ── Event listeners ───────────────────────────────────────────────────────────
function attachEventListeners() {
  if (userMenuBtn) userMenuBtn.addEventListener('click', toggleUserDropdown);
  if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);
  if (changePasswordLink) changePasswordLink.addEventListener('click', (e) => { e.preventDefault(); showChangePasswordModal(false); userDropdown.classList.remove('active'); });
  if (btnCloseChangePassword) btnCloseChangePassword.addEventListener('click', hideChangePasswordModal);
  if (btnCancelChangePassword) btnCancelChangePassword.addEventListener('click', hideChangePasswordModal);
  if (btnSaveChangePassword) btnSaveChangePassword.addEventListener('click', handleChangePassword);
  if (changePasswordForm) changePasswordForm.addEventListener('submit', handleChangePassword);
  if (btnRefreshLogs) btnRefreshLogs.addEventListener('click', loadSystemLogs);
  navItems.forEach(item => item.addEventListener('click', handleNavClick));
  document.addEventListener('click', (e) => { if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) userDropdown.classList.remove('active'); });

  // User modal
  const btnAddUser = document.getElementById('btn-add-user');
  if (btnAddUser) btnAddUser.addEventListener('click', openCreateUserModal);
  const btnCloseUM = document.getElementById('btn-close-user-modal');
  const btnCancelUM = document.getElementById('btn-cancel-user-modal');
  const btnSaveUM = document.getElementById('btn-save-user-modal');
  if (btnCloseUM) btnCloseUM.addEventListener('click', _hideUserModal);
  if (btnCancelUM) btnCancelUM.addEventListener('click', _hideUserModal);
  if (btnSaveUM) btnSaveUM.addEventListener('click', saveUser);
  const userModal = document.getElementById('user-modal');
  if (userModal) userModal.addEventListener('click', (e) => { if (e.target === userModal) _hideUserModal(); });

  // Reset password modal
  const btnCloseRP = document.getElementById('btn-close-reset-pw');
  const btnCancelRP = document.getElementById('btn-cancel-reset-pw');
  const btnSaveRP = document.getElementById('btn-save-reset-pw');
  if (btnCloseRP) btnCloseRP.addEventListener('click', _hideResetPwModal);
  if (btnCancelRP) btnCancelRP.addEventListener('click', _hideResetPwModal);
  if (btnSaveRP) btnSaveRP.addEventListener('click', saveResetPassword);
  // Users table search & filters
  const usersSearchInput = document.getElementById('users-search-input');
  const usersRoleFilter = document.getElementById('users-role-filter');
  const usersStatusFilter = document.getElementById('users-status-filter');
  if (usersSearchInput) {
    usersSearchInput.addEventListener('input', renderUsersTable);
  }
  if (usersRoleFilter) {
    usersRoleFilter.addEventListener('change', renderUsersTable);
  }
  if (usersStatusFilter) {
    usersStatusFilter.addEventListener('change', renderUsersTable);
  }
}

// Expose functions globally on window
window._canDo = _canDo;
window.loadUserInfo = loadUserInfo;
window.loadUsers = loadUsers;
window.renderUsersTable = renderUsersTable;
window.openCreateUserModal = openCreateUserModal;
window.openEditUserModal = openEditUserModal;
window.saveUser = saveUser;
window.deleteUser = deleteUser;
window.unlockUser = unlockUser;
window.openResetPasswordModal = openResetPasswordModal;
window.saveResetPassword = saveResetPassword;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  attachEventListeners();
  loadUserInfo().then(() => {
    if (document.getElementById('users-table-body')) {
      loadUsers();
    }
  });
});