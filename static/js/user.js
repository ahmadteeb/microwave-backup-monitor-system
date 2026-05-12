// Shared API Helper
async function fetchAPI(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP error ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error on ${url}:`, error);
    throw error;
  }
}

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

// ── Permission labels ─────────────────────────────────────────────────────────
const PERMISSION_LABELS = {
  'links.view': 'View links', 'links.add': 'Add links', 'links.edit': 'Edit links',
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
  'Links': ['links.view','links.add','links.edit','links.delete','links.ping','links.export'],
  'Users': ['users.view','users.add','users.edit','users.delete','users.reset_password','users.manage_permissions'],
  'Config': ['config.view','config.edit_smtp','config.edit_jumpserver','config.edit_app'],
  'Logs': ['logs.view_system','logs.view_ping','logs.export'],
  'Notifications': ['notifications.view_own','notifications.edit_own','notifications.manage_all']
};

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
    await fetchAPI('/api/auth/change-password', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: cur, new_password: np, confirm_password: cp }) });
    if (window.showToast) window.showToast('Password updated successfully.', 'success');
    forcePasswordChangeRequired = false;
    hideChangePasswordModal();
  } catch (error) { showChangePasswordError(error.message); }
  finally { if (window.setButtonLoading) window.setButtonLoading(btnSaveChangePassword, false); }
}

// ── Load user info ────────────────────────────────────────────────────────────
async function loadUserInfo() {
  try {
    const data = await fetchAPI('/api/auth/me');
    currentUser = data;
    userName.textContent = currentUser.full_name || currentUser.username;
    userRole.textContent = currentUser.role || 'Administrator';
    if (currentUser.force_password_change) { showChangePasswordModal(true); showSection('dashboard'); }
  } catch (error) {
    console.error('Failed to load user info', error);
    userName.textContent = 'Unknown User'; userRole.textContent = 'User';
  }
}

// ── System Logs ───────────────────────────────────────────────────────────────
async function loadSystemLogs() {
  if (!logsTableBody) return;
  logsTableBody.innerHTML = '<tr><td colspan="6">Loading logs...</td></tr>';
  try {
    const data = await fetchAPI('/api/logs/system?per_page=50');
    if (!data.logs || data.logs.length === 0) { logsTableBody.innerHTML = '<tr><td colspan="6">No logs available</td></tr>'; return; }
    logsTableBody.innerHTML = data.logs.map(log => `
      <tr>
        <td>${new Date(log.timestamp).toLocaleString()}</td>
        <td>${log.category || ''}</td>
        <td>${log.event || ''}</td>
        <td>${log.actor || ''}</td>
        <td>${log.target || ''}</td>
        <td>${log.detail || ''}</td>
      </tr>
    `).join('');
  } catch (error) { logsTableBody.innerHTML = '<tr><td colspan="6">Unable to load logs.</td></tr>'; }
}

// ── Users Table ───────────────────────────────────────────────────────────────
function _roleBadgeClass(role) {
  if (role === 'admin') return 'role-admin';
  if (role === 'operator') return 'role-operator';
  return 'role-viewer';
}
function _statusBadge(status) {
  if (status === 'Active') return '<span class="status-badge status-active">Active</span>';
  if (status === 'Locked') return '<span class="status-badge status-locked">Locked</span>';
  return '<span class="status-badge status-inactive">Inactive</span>';
}
function _canDo(perm) { return currentUser && currentUser.permissions && currentUser.permissions[perm]; }

async function loadUsers() {
  if (!usersTableBody) return;
  usersTableBody.innerHTML = '<tr><td colspan="7">Loading users...</td></tr>';
  try {
    const data = await fetchAPI('/api/users');
    if (!data.users || data.users.length === 0) { usersTableBody.innerHTML = '<tr><td colspan="7">No users found</td></tr>'; return; }
    usersTableBody.innerHTML = data.users.map(user => {
      let actions = '';
      if (_canDo('users.edit'))
        actions += `<button class="btn-icon-sm" title="Edit" onclick="openEditUserModal(${user.id})"><i class="fa-solid fa-pen"></i></button>`;
      if (_canDo('users.reset_password'))
        actions += `<button class="btn-icon-sm" title="Reset Password" onclick="openResetPasswordModal(${user.id}, '${user.username}')"><i class="fa-solid fa-key"></i></button>`;

      if (user.is_locked && _canDo('users.edit'))
        actions += `<button class="btn-icon-sm btn-icon-warning" title="Unlock" onclick="unlockUser(${user.id})"><i class="fa-solid fa-lock-open"></i></button>`;
      if (_canDo('users.delete') && user.id !== currentUser.id)
        actions += `<button class="btn-icon-sm btn-icon-danger" title="Delete" onclick="deleteUser(${user.id}, '${user.username}')"><i class="fa-solid fa-trash"></i></button>`;
      if (!actions) actions = '<span class="text-muted">—</span>';
      return `<tr>
        <td>${user.full_name}</td>
        <td class="text-mono text-secondary">${user.username}</td>
        <td>${user.email}</td>
        <td><span class="role-badge ${_roleBadgeClass(user.role)}">${user.role.toUpperCase()}</span></td>
        <td>${_statusBadge(user.status)}</td>
        <td>${user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '<span class="text-muted">Never</span>'}</td>
        <td style="text-align: right;">${actions}</td>
      </tr>`;
    }).join('');
  } catch (error) { usersTableBody.innerHTML = '<tr><td colspan="7">Unable to load users.</td></tr>'; }
}

// ── User Modal (Create / Edit) ────────────────────────────────────────────────
function _showUserModal() { document.getElementById('user-modal').classList.add('active'); }
function _hideUserModal() { document.getElementById('user-modal').classList.remove('active'); }

async function _populateRolesSelect() {
  const select = document.getElementById('user-modal-role');
  try {
    const data = await fetchAPI('/api/roles');
    if (data.roles) {
      select.innerHTML = data.roles.map(r => `<option value="${r.name}">${r.name.toUpperCase()}</option>`).join('');
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
  document.getElementById('user-modal-role').value = 'operator';
  document.getElementById('user-modal-password').value = '';
  document.getElementById('user-modal-password-group').classList.remove('hidden');
  document.getElementById('user-modal-active').checked = true;
  document.getElementById('user-modal-force-pw').checked = true;
  document.getElementById('user-modal-error').classList.add('hidden');
  _showUserModal();
}

async function openEditUserModal(userId) {
  try {
    const [userData, _] = await Promise.all([
      fetchAPI(`/api/users/${userId}`),
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
    document.getElementById('user-modal-password-group').classList.add('hidden');
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
  const payload = {
    full_name: document.getElementById('user-modal-fullname').value.trim(),
    email: document.getElementById('user-modal-email').value.trim(),
    role: document.getElementById('user-modal-role').value,
    is_active: document.getElementById('user-modal-active').checked,
    force_password_change: document.getElementById('user-modal-force-pw').checked
  };
  if (!isEdit) {
    payload.username = document.getElementById('user-modal-username').value.trim();
    const pw = document.getElementById('user-modal-password').value;
    if (pw) payload.password = pw;
  }
  if (!payload.full_name || !payload.email || (!isEdit && !payload.username)) {
    errText.textContent = 'Please fill in all required fields.'; errEl.classList.remove('hidden'); return;
  }
  const btn = document.getElementById('btn-save-user-modal');
  if (window.setButtonLoading) window.setButtonLoading(btn, true, 'SAVING...');
  try {
    if (isEdit) {
      await fetchAPI(`/api/users/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      window.showToast('User updated successfully', 'success');
    } else {
      await fetchAPI('/api/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      window.showToast('User created successfully', 'success');
    }
    _hideUserModal(); loadUsers();
  } catch (error) { errText.textContent = error.message; errEl.classList.remove('hidden'); }
  finally { if (window.setButtonLoading) window.setButtonLoading(btn, false); }
}

async function deleteUser(userId, username) {
  const confirmed = await window.showConfirm({
    title: 'DELETE USER', message: `Are you sure you want to delete <strong>${username}</strong>?<br>This action cannot be undone.`,
    confirmText: 'DELETE', cancelText: 'CANCEL', variant: 'danger'
  });
  if (!confirmed) return;
  try {
    await fetchAPI(`/api/users/${userId}`, { method: 'DELETE' });
    window.showToast('User deleted', 'success'); loadUsers();
  } catch (error) { window.showToast('Failed to delete user: ' + error.message, 'error'); }
}

async function unlockUser(userId) {
  const confirmed = await window.showConfirm({
    title: 'UNLOCK USER', message: 'Unlock this user account and reset the failed login counter?',
    confirmText: 'UNLOCK', cancelText: 'CANCEL', variant: 'warning'
  });
  if (!confirmed) return;
  try {
    await fetchAPI(`/api/users/${userId}/unlock`, { method: 'POST' });
    window.showToast('User unlocked', 'success'); loadUsers();
  } catch (error) { window.showToast('Failed to unlock user: ' + error.message, 'error'); }
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
  const np = document.getElementById('reset-pw-new').value;
  const cp = document.getElementById('reset-pw-confirm').value;
  const force = document.getElementById('reset-pw-force').checked;
  if (!np || np.length < 8) { errText.textContent = 'Password must be at least 8 characters.'; errEl.classList.remove('hidden'); return; }
  if (np !== cp) { errText.textContent = 'Passwords do not match.'; errEl.classList.remove('hidden'); return; }
  const btn = document.getElementById('btn-save-reset-pw');
  if (window.setButtonLoading) window.setButtonLoading(btn, true, 'RESETTING...');
  try {
    await fetchAPI(`/api/users/${userId}/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: np, confirm_password: cp, force_password_change: force }) });
    window.showToast('Password reset successfully', 'success'); _hideResetPwModal(); loadUsers();
  } catch (error) { errText.textContent = error.message; errEl.classList.remove('hidden'); }
  finally { if (window.setButtonLoading) window.setButtonLoading(btn, false); }
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
  try { await fetchAPI('/api/auth/logout', { method: 'POST' }); } catch (error) {}
  window.location.href = '/login';
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
  const rpModal = document.getElementById('reset-password-modal');
  if (rpModal) rpModal.addEventListener('click', (e) => { if (e.target === rpModal) _hideResetPwModal(); });

}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  attachEventListeners();
  loadUserInfo();
});