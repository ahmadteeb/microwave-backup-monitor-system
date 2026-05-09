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
const loginForm = document.getElementById('login-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const submitBtn = loginForm.querySelector('button[type="submit"]');

// Show error message
function showError(message) {
  errorText.textContent = message;
  errorMessage.classList.remove('hidden');
  if (window.showToast) {
    window.showToast(message, 'error');
  }
}

// Hide error message
function hideError() {
  errorMessage.classList.add('hidden');
}

// Handle login form submission
async function handleLogin(event) {
  event.preventDefault();
  hideError();

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showError('Username and password are required.');
    return;
  }

  // Show loading state on submit button
  if (window.setButtonLoading) {
    window.setButtonLoading(submitBtn, true, 'AUTHENTICATING...');
  }

  try {
    const response = await fetchAPI('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    // Redirect to dashboard on success
    window.location.href = '/';
  } catch (error) {
    showError(error.message);
  } finally {
    if (window.setButtonLoading) {
      window.setButtonLoading(submitBtn, false);
    }
  }
}

// Event listeners
loginForm.addEventListener('submit', handleLogin);

// Auto-focus username field
document.addEventListener('DOMContentLoaded', () => {
  usernameInput.focus();
});