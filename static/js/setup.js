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
const flaskSecretKey = document.getElementById('session-secret-key');
const btnGenerateKey = document.getElementById('btn-generate-key');
const btnTestSmtp = document.getElementById('btn-test-smtp');
const btnTestJumpServer = document.getElementById('btn-test-jumpserver');
const dbEngine = document.getElementById('db-engine');
const dbSqlitePath = document.getElementById('db-sqlite-path');
const dbHost = document.getElementById('db-host');
const dbPort = document.getElementById('db-port');
const dbUsername = document.getElementById('db-username');
const dbPassword = document.getElementById('db-password');
const dbDatabase = document.getElementById('db-database');
const externalDbEnabled = document.getElementById('external-db-enabled');
const externalDbFields = document.querySelector('.external-db-fields');
const externalDbHost = document.getElementById('external-db-host');
const externalDbPort = document.getElementById('external-db-port');
const externalDbUsername = document.getElementById('external-db-username');
const externalDbPassword = document.getElementById('external-db-password');
const externalDbDatabase = document.getElementById('external-db-database');
const btnTestExternalDb = document.getElementById('btn-test-external-db');
const adminFullName = document.getElementById('admin-full-name');
const smtpEnabled = document.getElementById('smtp-enabled');
const smtpFields = document.querySelectorAll('.smtp-field');
const jumpEnabled = document.getElementById('jumpserver-enabled');
const jumpFields = document.querySelectorAll('.jump-field');

// Current step
let currentStep = 1;

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

  btnPrev.classList.toggle('hidden', currentStep === 1);
  btnNext.classList.toggle('hidden', currentStep === 5);
  btnComplete.classList.toggle('hidden', currentStep !== 5);
}

// Update visible fields based on DB engine and SMTP toggle
function refreshVisibility() {
  const engine = dbEngine.value;
  document.querySelectorAll('.db-field').forEach(field => field.classList.add('hidden'));

  if (engine === 'sqlite') {
    document.querySelector('.sqlite-field').classList.remove('hidden');
  } else {
    document.querySelector('.sql-field').classList.remove('hidden');
    if (engine === 'postgres' && (dbPort.value === '' || dbPort.value === '3306')) {
      dbPort.value = '5432';
    } else if (engine === 'mysql' && (dbPort.value === '' || dbPort.value === '5432')) {
      dbPort.value = '3306';
    }
  }

  externalDbFields.classList.toggle('hidden', !externalDbEnabled.checked);

  smtpFields.forEach(field => {
    field.classList.toggle('hidden', !smtpEnabled.checked);
  });

  jumpFields.forEach(field => {
    field.classList.toggle('hidden', !jumpEnabled.checked);
  });
}

// Scroll setup form to top
function scrollFormTop() {
  setupForm.scrollTo({ top: 0, behavior: 'smooth' });
}

// Navigate to next step
function nextStep() {
  if (currentStep < 5) {
    currentStep++;
    updateProgress();
    scrollFormTop();
  }
}

// Navigate to previous step
function prevStep() {
  if (currentStep > 1) {
    currentStep--;
    updateProgress();
    scrollFormTop();
  }
}

// Validate current step
function validateCurrentStep() {
  hideError();

  switch (currentStep) {
    case 1:
      return validateDatabaseConfig();
    case 2:
      return validateAdminUser();
    case 3:
      return validateSmtpConfig();
    case 4:
      return validateJumpServer();
    default:
      return true;
  }
}

function validateExternalDbConfig() {
  if (!externalDbEnabled.checked) {
    return true;
  }

  const host = externalDbHost.value.trim();
  const port = parseInt(externalDbPort.value, 10);
  const username = externalDbUsername.value.trim();
  const database = externalDbDatabase.value.trim();

  if (!host) {
    showError('External DB host is required when enabled.');
    return false;
  }

  if (!port || port < 1 || port > 65535) {
    showError('Valid external DB port is required.');
    return false;
  }

  if (!username) {
    showError('External DB username is required when enabled.');
    return false;
  }

  if (!database) {
    showError('External DB database name is required when enabled.');
    return false;
  }

  return true;
}

// Validate database config step
function validateDatabaseConfig() {
  const secretKey = flaskSecretKey.value.trim();
  const engine = dbEngine.value;
  const sqlitePath = dbSqlitePath.value.trim();
  const host = dbHost.value.trim();
  const port = parseInt(dbPort.value, 10);
  const username = dbUsername.value.trim();
  const database = dbDatabase.value.trim();

  if (!secretKey || secretKey.length < 16) {
    showError('Flask Secret Key is required and must be at least 16 characters.');
    return false;
  }

  if (engine === 'sqlite') {
    if (!sqlitePath) {
      showError('SQLite path is required.');
      return false;
    }
    if (!validateExternalDbConfig()) {
      return false;
    }
    return true;
  }

  if (!host) {
    showError('Database host is required.');
    return false;
  }

  if (!port || port < 1 || port > 65535) {
    showError('Valid database port is required.');
    return false;
  }

  if (!username) {
    showError('Database username is required.');
    return false;
  }

  if (!database) {
    showError('Database name is required.');
    return false;
  }

  if (!validateExternalDbConfig()) {
    return false;
  }

  return true;
}

// Validate admin user step
function validateAdminUser() {
  const username = document.getElementById('admin-username').value.trim();
  const fullName = adminFullName.value.trim();
  const email = document.getElementById('admin-email').value.trim();
  const password = document.getElementById('admin-password').value;
  const confirmPassword = document.getElementById('admin-confirm-password').value;

  if (!username) {
    showError('Username is required.');
    return false;
  }

  if (!fullName) {
    showError('Full name is required.');
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
  if (!smtpEnabled.checked) {
    return true;
  }

  const server = document.getElementById('smtp-server').value.trim();
  const port = parseInt(document.getElementById('smtp-port').value, 10);
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
  if (!jumpEnabled.checked) {
    return true;
  }

  const host = document.getElementById('jump-host').value.trim();
  const port = parseInt(document.getElementById('jump-port').value, 10);
  const username = document.getElementById('jump-username').value.trim();
  const password = document.getElementById('jump-password').value;

  if (!host) {
    showError('Jump server host is required when enabled.');
    return false;
  }

  if (!port || port < 1 || port > 65535) {
    showError('Valid SSH port is required when jump server is enabled.');
    return false;
  }

  if (!username) {
    showError('SSH username is required when jump server is enabled.');
    return false;
  }

  if (!password) {
    showError('SSH password is required when jump server is enabled.');
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

// Handle test SMTP connection
async function handleTestSmtp() {
  if (!validateSmtpConfig()) return;
  
  const payload = {
    host: document.getElementById('smtp-server').value.trim(),
    port: parseInt(document.getElementById('smtp-port').value, 10),
    username: document.getElementById('smtp-username').value.trim(),
    password: document.getElementById('smtp-password').value,
    from_address: document.getElementById('smtp-from-email').value.trim(),
    use_tls: document.getElementById('smtp-use-tls').value === 'true',
    use_ssl: false
  };

  const originalText = btnTestSmtp.innerHTML;
  btnTestSmtp.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> TESTING...';
  btnTestSmtp.disabled = true;

  try {
    const result = await fetchAPI('/api/setup/test-smtp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (window.showToast) {
      window.showToast('SMTP Connection Successful', 'success');
    }
  } catch (error) {
    if (window.showAlert) {
      window.showAlert({
        title: 'SMTP TEST FAILED',
        message: error.message || 'Failed to connect to SMTP server.',
        type: 'error',
        buttonText: 'CLOSE'
      });
    } else {
      alert(`SMTP Test Failed: ${error.message}`);
    }
  } finally {
    btnTestSmtp.innerHTML = originalText;
    btnTestSmtp.disabled = false;
  }
}

// Handle test external DB connection
async function handleTestExternalDb() {
  if (!externalDbEnabled.checked) {
    window.showToast('Enable the external DB before testing.', 'warning');
    return;
  }

  const payload = {
    host: externalDbHost.value.trim(),
    port: parseInt(externalDbPort.value, 10),
    username: externalDbUsername.value.trim(),
    password: externalDbPassword.value,
    database: externalDbDatabase.value.trim()
  };

  if (!payload.host || !payload.port || !payload.username || !payload.database) {
    showError('Fill required external DB fields before testing.');
    return;
  }

  const originalText = btnTestExternalDb.innerHTML;
  btnTestExternalDb.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> TESTING...';
  btnTestExternalDb.disabled = true;

  try {
    await fetchAPI('/api/setup/test-external-db', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    window.showToast('External util DB connection successful', 'success');
  } catch (error) {
    window.showToast('External DB test failed: ' + error.message, 'error');
  } finally {
    btnTestExternalDb.innerHTML = originalText;
    btnTestExternalDb.disabled = false;
  }
}

// Handle test jump server connection
async function handleTestJumpServer() {
  if (!validateJumpServer()) return;

  const payload = {
    host: document.getElementById('jump-host').value.trim(),
    port: parseInt(document.getElementById('jump-port').value, 10),
    username: document.getElementById('jump-username').value.trim(),
    password: document.getElementById('jump-password').value
  };

  const originalText = btnTestJumpServer.innerHTML;
  btnTestJumpServer.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> TESTING...';
  btnTestJumpServer.disabled = true;

  try {
    const result = await fetchAPI('/api/setup/test-jumpserver', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (window.showToast) {
      window.showToast('Jump Server Connection Successful', 'success');
    }
  } catch (error) {
    if (window.showAlert) {
      window.showAlert({
        title: 'JUMP SERVER TEST FAILED',
        message: error.message || 'Failed to connect to Jump Server.',
        type: 'error',
        buttonText: 'CLOSE'
      });
    } else {
      alert(`Jump Server Test Failed: ${error.message}`);
    }
  } finally {
    btnTestJumpServer.innerHTML = originalText;
    btnTestJumpServer.disabled = false;
  }
}

// Build request payload
function getFormPayload() {
  const smtpActive = smtpEnabled.checked;
  return {
    secret_key: flaskSecretKey.value.trim(),
    db_config: {
      engine: dbEngine.value,
      path: dbSqlitePath.value.trim(),
      host: dbHost.value.trim(),
      port: parseInt(dbPort.value, 10),
      username: dbUsername.value.trim(),
      password: dbPassword.value,
      database: dbDatabase.value.trim()
    },
    full_name: adminFullName.value.trim(),
    username: document.getElementById('admin-username').value.trim(),
    email: document.getElementById('admin-email').value.trim(),
    password: document.getElementById('admin-password').value,
    confirm_password: document.getElementById('admin-confirm-password').value,
    smtp_enabled: smtpActive,
    smtp: smtpActive
      ? {
        host: document.getElementById('smtp-server').value.trim(),
        port: parseInt(document.getElementById('smtp-port').value, 10),
        username: document.getElementById('smtp-username').value.trim(),
        password: document.getElementById('smtp-password').value,
        from_address: document.getElementById('smtp-from-email').value.trim(),
        use_tls: document.getElementById('smtp-use-tls').value === 'true',
        use_ssl: false
      }
      : {},
    external_db_config: externalDbEnabled.checked
      ? {
        host: externalDbHost.value.trim(),
        port: parseInt(externalDbPort.value, 10),
        username: externalDbUsername.value.trim(),
        password: externalDbPassword.value,
        database: externalDbDatabase.value.trim()
      }
      : {},
    jumpserver: {
      host: document.getElementById('jump-host').value.trim(),
      port: parseInt(document.getElementById('jump-port').value, 10),
      username: document.getElementById('jump-username').value.trim(),
      password: document.getElementById('jump-password').value
    }
  };
}

// Handle setup completion
async function handleComplete(event) {
  event.preventDefault();
  hideError();

  if (!validateCurrentStep()) {
    return;
  }

  const formData = getFormPayload();

  // Show loading overlay
  const loader = window.showLoading ? window.showLoading('Completing setup...') : null;
  if (window.setButtonLoading) {
    window.setButtonLoading(btnComplete, true, 'COMPLETING...');
  }

  try {
    await fetchAPI('/api/setup/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    if (loader) loader.close();

    if (window.showAlert) {
      await window.showAlert({
        title: 'SETUP COMPLETE',
        message: 'System configuration completed successfully. You will be redirected to the login page.',
        type: 'success',
        buttonText: 'CONTINUE'
      });
      window.location.href = '/login';
    } else {
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    }
  } catch (error) {
    if (loader) loader.close();
    if (window.setButtonLoading) {
      window.setButtonLoading(btnComplete, false);
    }
    showError(error.message);
  }
}

// Event listeners
btnNext.addEventListener('click', handleNext);
btnPrev.addEventListener('click', handlePrev);
setupForm.addEventListener('submit', handleComplete);
if (btnTestSmtp) btnTestSmtp.addEventListener('click', handleTestSmtp);
if (btnTestJumpServer) btnTestJumpServer.addEventListener('click', handleTestJumpServer);
if (btnTestExternalDb) btnTestExternalDb.addEventListener('click', handleTestExternalDb);

btnGenerateKey.addEventListener('click', () => {
  const array = new Uint8Array(32);
  window.crypto.getRandomValues(array);
  flaskSecretKey.value = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  if (window.showToast) {
    window.showToast('Secret key generated', 'success');
  }
});

externalDbEnabled.addEventListener('change', refreshVisibility);
dbEngine.addEventListener('change', refreshVisibility);
smtpEnabled.addEventListener('change', refreshVisibility);
jumpEnabled.addEventListener('change', refreshVisibility);

document.addEventListener('DOMContentLoaded', () => {
  refreshVisibility();
  updateProgress();
});