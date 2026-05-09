// DOM Elements
const userMenuBtn = document.getElementById('user-menu-btn');
const userDropdown = document.getElementById('user-dropdown');
const userName = document.getElementById('user-name');
const userRole = document.getElementById('user-role');
const logoutBtn = document.getElementById('logout-btn');

// Load user info
async function loadUserInfo() {
  try {
    const data = await window.fetchAPI('/api/profile');
    userName.textContent = data.user.username;
    userRole.textContent = data.user.role || 'Administrator';
  } catch (error) {
    console.error("Failed to load user info", error);
    userName.textContent = 'Unknown User';
    userRole.textContent = 'User';
  }
}

// Handle logout
async function handleLogout(event) {
  event.preventDefault();

  try {
    await window.fetchAPI('/api/auth/logout', {
      method: 'POST'
    });
  } catch (error) {
    console.error("Logout error", error);
  }

  // Redirect to login regardless of API response
  window.location.href = '/login';
}

// Toggle user dropdown
function toggleUserDropdown() {
  userDropdown.classList.toggle('active');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  if (!userMenuBtn.contains(e.target) && !userDropdown.contains(e.target)) {
    userDropdown.classList.remove('active');
  }
});

// Event listeners
userMenuBtn.addEventListener('click', toggleUserDropdown);
logoutBtn.addEventListener('click', handleLogout);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  loadUserInfo();
});