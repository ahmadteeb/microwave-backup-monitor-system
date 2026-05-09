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
const setupForm = document.getElementById('setup-form');
const progressSteps = document.querySelectorAll('.progress-step');
const setupSteps = document.querySelectorAll('.setup-step');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');
const btnComplete = document.getElementById('btn-complete');
const errorMessage = document.getElementById('error-message');
const errorText = document.getElementById('error-text');

// Current step
let currentStep = 1;

// Show error message
function showError(message) {
  errorText.textContent = message;
  errorMessage.classList.remove('hidden');
}

// Hide error message
function hideError() {
  errorMessage.classList.add('hidden');
}

// Update progress indicators
function updateProgress() {
  progressSteps.forEach((step, index) => {
    if (index + 1 <= currentStep) {
      step.classList.add('active');
    } else {
      step.classList.remove('active');
    }
  });

  setupSteps.forEach((step, index) => {
    if (index + 1 === currentStep) {
      step.classList.add('active');
    } else {
      step.classList.remove('active');
    }
  });

  // Update button visibility
  btnPrev.classList.toggle('hidden', currentStep === 1);
  btnNext.classList.toggle('hidden', currentStep === 4);
  btnComplete.classList.toggle('hidden', currentStep !== 4);
}

// Navigate to next step
function nextStep() {
  if (currentStep < 4) {
    currentStep++;
    updateProgress();
  }
}

// Navigate to previous step
function prevStep() {
  if (currentStep > 1) {
    currentStep--;
    updateProgress();
  }
}

// Validate current step
function validateCurrentStep() {
  hideError();

  switch (currentStep) {
    case 1:
      return validateAdminUser();
    case 2:
      return validateSmtpConfig();
    case 3:
      return validateJumpServer();
    default:
      return true;
  }
}

// Validate admin user step
function validateAdminUser() {
  const username = document.getElementById('admin-username').value.trim();
  const email = document.getElementById('admin-email').value.trim();
  const password = document.getElementById('admin-password').value;
  const confirmPassword = document.getElementById('admin-confirm-password').value;

  if (!username) {
    showError('Username is required.');
    return false;
  }

  if (!email) {
    showError('Email is required.');
    return false;
  }

  if (!password) {
    showError('Password is required.');
    return false;
  }

  if (password.length < 8) {
    showError('Password must be at least 8 characters long.');
    return false;
  }

  if (password !== confirmPassword) {
    showError('Passwords do not match.');
    return false;
  }

  return true;
}

// Validate SMTP config step
function validateSmtpConfig() {
  const server = document.getElementById('smtp-server').value.trim();
  const port = document.getElementById('smtp-port').value;
  const username = document.getElementById('smtp-username').value.trim();
  const password = document.getElementById('smtp-password').value;
  const fromEmail = document.getElementById('smtp-from-email').value.trim();

  if (!server) {
    showError('SMTP server is required.');
    return false;
  }

  if (!port || port < 1 || port > 65535) {
    showError('Valid SMTP port is required.');
    return false;
  }

  if (!fromEmail) {
    showError('From email is required.');
    return false;
  }

  return true;
}

// Validate jump server step
function validateJumpServer() {
  const host = document.getElementById('jump-host').value.trim();
  const port = document.getElementById('jump-port').value;
  const username = document.getElementById('jump-username').value.trim();
  const password = document.getElementById('jump-password').value;

  if (!host) {
    showError('Jump server host is required.');
    return false;
  }

  if (!port || port < 1 || port > 65535) {
    showError('Valid SSH port is required.');
    return false;
  }

  if (!username) {
    showError('SSH username is required.');
    return false;
  }

  if (!password) {
    showError('SSH password is required.');
    return false;
  }

  return true;
}

// Handle next button click
function handleNext() {
  if (validateCurrentStep()) {
    nextStep();
  }
}

// Handle previous button click
function handlePrev() {
  prevStep();
}

// Handle setup completion
async function handleComplete(event) {
  event.preventDefault();
  hideError();

  // Collect all form data
  const formData = {
    admin_username: document.getElementById('admin-username').value.trim(),
    admin_email: document.getElementById('admin-email').value.trim(),
    admin_password: document.getElementById('admin-password').value,
    smtp_server: document.getElementById('smtp-server').value.trim(),
    smtp_port: parseInt(document.getElementById('smtp-port').value),
    smtp_username: document.getElementById('smtp-username').value.trim(),
    smtp_password: document.getElementById('smtp-password').value,
    smtp_from_email: document.getElementById('smtp-from-email').value.trim(),
    smtp_use_tls: document.getElementById('smtp-use-tls').value === 'true',
    jump_host: document.getElementById('jump-host').value.trim(),
    jump_port: parseInt(document.getElementById('jump-port').value),
    jump_username: document.getElementById('jump-username').value.trim(),
    jump_password: document.getElementById('jump-password').value
  };

  try {
    const response = await fetchAPI('/api/setup/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    // Show success and redirect
    setTimeout(() => {
      window.location.href = '/login';
    }, 2000);
  } catch (error) {
    showError(error.message);
  }
}

// Event listeners
btnNext.addEventListener('click', handleNext);
btnPrev.addEventListener('click', handlePrev);
setupForm.addEventListener('submit', handleComplete);

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  updateProgress();
});