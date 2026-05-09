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
const changePasswordForm = document.getElementById('change-password-form');
const currentPasswordInput = document.getElementById('current-password');
const newPasswordInput = document.getElementById('new-password');
const confirmPasswordInput = document.getElementById('confirm-password');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const successMessage = document.getElementById('success-message');

// Show error message
function showError(message) {
  errorText.textContent = message;
  errorMessage.classList.remove('hidden');
  successMessage.classList.add('hidden');
}

// Hide error message
function hideError() {
  errorMessage.classList.add('hidden');
}

// Show success message
function showSuccess() {
  successMessage.classList.remove('hidden');
  errorMessage.classList.add('hidden');
}

// Handle change password form submission
async function handleChangePassword(event) {
  event.preventDefault();
  hideError();

  const currentPassword = currentPasswordInput.value;
  const newPassword = newPasswordInput.value;
  const confirmPassword = confirmPasswordInput.value;

  if (!currentPassword) {
    showError('Current password is required.');
    return;
  }

  if (!newPassword) {
    showError('New password is required.');
    return;
  }

  if (newPassword.length < 8) {
    showError('New password must be at least 8 characters long.');
    return;
  }

  if (newPassword !== confirmPassword) {
    showError('New password and confirmation do not match.');
    return;
  }

  if (currentPassword === newPassword) {
    showError('New password must be different from current password.');
    return;
  }

  try {
    const response = await fetchAPI('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      })
    });

    showSuccess();

    // Redirect to dashboard after success
    setTimeout(() => {
      window.location.href = '/';
    }, 2000);
  } catch (error) {
    showError(error.message);
  }
}

// Event listeners
changePasswordForm.addEventListener('submit', handleChangePassword);

// Auto-focus current password field
document.addEventListener('DOMContentLoaded', () => {
  currentPasswordInput.focus();
});