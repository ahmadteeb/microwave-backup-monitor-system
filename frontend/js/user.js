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

// DOM Elements
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

function showSection(sectionName) {
  const sectionMap = {
    dashboard: dashboardSection,
    logs: logsSection,
    users: usersSection
  };

  Object.entries(sectionMap).forEach(([key, section]) => {
    if (!section) return;
    section.classList.toggle('hidden', key !== sectionName);
  });

  navItems.forEach(item => {
    item.classList.toggle('active', item.dataset.section === sectionName);
  });
}

function showChangePasswordModal(required = false) {
  if (!changePasswordModal) return;
  forcePasswordChangeRequired = required;
  changePasswordModal.classList.remove('hidden');
  if (forcePasswordChangeRequired) {
    btnCloseChangePassword?.classList.add('hidden');
    btnCancelChangePassword?.classList.add('hidden');
  } else {
    btnCloseChangePassword?.classList.remove('hidden');
    btnCancelChangePassword?.classList.remove('hidden');
  }
  clearChangePasswordError();
  currentPasswordInput?.focus();
}

function hideChangePasswordModal() {
  if (forcePasswordChangeRequired) return;
  if (!changePasswordModal) return;
  changePasswordModal.classList.add('hidden');
}

function clearChangePasswordError() {
  if (!changePasswordError) return;
  changePasswordError.classList.add('hidden');
  changePasswordErrorText.textContent = '';
}

function showChangePasswordError(message) {
  if (!changePasswordError) return;
  changePasswordErrorText.textContent = message;
  changePasswordError.classList.remove('hidden');
  if (window.showToast) {
    window.showToast(message, 'error');
  }
}

async function handleChangePassword(event) {
  if (event) event.preventDefault();
  clearChangePasswordError();

  const currentPassword = currentPasswordInput?.value || '';
  const newPassword = newPasswordInput?.value || '';
  const confirmPassword = confirmPasswordInput?.value || '';

  if (!newPassword || newPassword.length < 8) {
    showChangePasswordError('New password must be at least 8 characters.');
    return;
  }

  if (newPassword !== confirmPassword) {
    showChangePasswordError('New password and confirmation do not match.');
    return;
  }

  if (!forcePasswordChangeRequired && !currentPassword) {
    showChangePasswordError('Current password is required.');
    return;
  }

  if (window.setButtonLoading) {
    window.setButtonLoading(btnSaveChangePassword, true, 'UPDATING...');
  }

  try {
    await fetchAPI('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      })
    });

    if (window.showToast) {
      window.showToast('Password updated successfully.', 'success');
    }

    forcePasswordChangeRequired = false;
    hideChangePasswordModal();
  } catch (error) {
    showChangePasswordError(error.message);
  } finally {
    if (window.setButtonLoading) {
      window.setButtonLoading(btnSaveChangePassword, false);
    }
  }
}

async function loadUserInfo() {
  try {
    const data = await fetchAPI('/api/profile');
    currentUser = data.user;
    userName.textContent = currentUser.full_name || currentUser.username;
    userRole.textContent = currentUser.role || 'Administrator';

    if (currentUser.force_password_change) {
      showChangePasswordModal(true);
      showSection('dashboard');
    }
  } catch (error) {
    console.error('Failed to load user info', error);
    userName.textContent = 'Unknown User';
    userRole.textContent = 'User';
  }
}

async function loadSystemLogs() {
  if (!logsTableBody) return;
  logsTableBody.innerHTML = '<tr><td colspan="6">Loading logs...</td></tr>';
  try {
    const data = await fetchAPI('/api/logs/system?per_page=50');
    if (!data.logs || data.logs.length === 0) {
      logsTableBody.innerHTML = '<tr><td colspan="6">No logs available</td></tr>';
      return;
    }
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
  } catch (error) {
    logsTableBody.innerHTML = '<tr><td colspan="6">Unable to load logs.</td></tr>';
    console.error('Failed to load system logs', error);
  }
}

async function loadUsers() {
  if (!usersTableBody) return;
  usersTableBody.innerHTML = '<tr><td colspan="6">Loading users...</td></tr>';
  try {
    const data = await fetchAPI('/api/users');
    if (!data.users || data.users.length === 0) {
      usersTableBody.innerHTML = '<tr><td colspan="6">No users found</td></tr>';
      return;
    }
    usersTableBody.innerHTML = data.users.map(user => `
      <tr>
        <td>${user.full_name}</td>
        <td>${user.email}</td>
        <td>${user.role}</td>
        <td>${user.status}</td>
        <td>${user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}</td>
        <td>${user.is_active ? 'Active' : 'Inactive'}</td>
      </tr>
    `).join('');
  } catch (error) {
    usersTableBody.innerHTML = '<tr><td colspan="6">Unable to load users.</td></tr>';
    console.error('Failed to load users', error);
  }
}

function handleNavClick(event) {
  const target = event.currentTarget;
  const section = target.dataset.section;
  if (!section) return;
  showSection(section);
  if (section === 'logs') {
    loadSystemLogs();
  } else if (section === 'users') {
    loadUsers();
  }
}

function toggleUserDropdown() {
  userDropdown.classList.toggle('active');
}

async function handleLogout(event) {
  event.preventDefault();

  try {
    await fetchAPI('/api/auth/logout', { method: 'POST' });
  } catch (error) {
    console.error('Logout error', error);
  }

  window.location.href = '/login';
}

function attachEventListeners() {
  if (userMenuBtn) {
    userMenuBtn.addEventListener('click', toggleUserDropdown);
  }
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
  if (changePasswordLink) {
    changePasswordLink.addEventListener('click', (event) => {
      event.preventDefault();
      showChangePasswordModal(false);
      userDropdown.classList.remove('active');
    });
  }
  if (btnCloseChangePassword) {
    btnCloseChangePassword.addEventListener('click', hideChangePasswordModal);
  }
  if (btnCancelChangePassword) {
    btnCancelChangePassword.addEventListener('click', hideChangePasswordModal);
  }
  if (btnSaveChangePassword) {
    btnSaveChangePassword.addEventListener('click', handleChangePassword);
  }
  if (changePasswordForm) {
    changePasswordForm.addEventListener('submit', handleChangePassword);
  }
  if (btnRefreshLogs) {
    btnRefreshLogs.addEventListener('click', loadSystemLogs);
  }
  navItems.forEach(item => item.addEventListener('click', handleNavClick));
  document.addEventListener('click', (e) => {
    if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
      userDropdown.classList.remove('active');
    }
  });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  attachEventListeners();
  loadUserInfo();
});