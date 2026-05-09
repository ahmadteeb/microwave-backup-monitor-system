// DOM Elements
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const btnCloseSettings = document.getElementById('btn-close-settings');
const btnCancelSettings = document.getElementById('btn-cancel-settings');
const btnSaveSettings = document.getElementById('btn-save-settings');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanes = document.querySelectorAll('.tab-pane');
const btnTestSmtp = document.getElementById('btn-test-smtp');
const btnTestJumpserver = document.getElementById('btn-test-jumpserver');

// Current settings data
let currentSettings = {};

// Load settings
async function loadSettings() {
  try {
    const [appSettings, smtpSettings, jumpSettings, notificationSettings] = await Promise.all([
      window.fetchAPI('/api/settings/app'),
      window.fetchAPI('/api/settings/smtp'),
      window.fetchAPI('/api/settings/jumpserver'),
      window.fetchAPI('/api/notifications/subscriptions')
    ]);

    currentSettings = {
      app: appSettings.app || {},
      smtp: smtpSettings.smtp || {},
      jump: jumpSettings.jumpserver || {},
      notifications: notificationSettings.subscriptions || {}
    };

    populateForm();
  } catch (error) {
    console.error("Failed to load settings", error);
    window.showToast('Failed to load settings: ' + error.message, 'error');
  }
}

// Populate form with current settings
function populateForm() {
  // General settings
  document.getElementById('ping-interval').value = currentSettings.app.ping_interval_seconds || 60;
  document.getElementById('session-timeout').value = currentSettings.app.session_timeout_minutes || 480;

  // SMTP settings
  document.getElementById('smtp-enabled').checked = currentSettings.smtp.enabled || false;
  document.getElementById('smtp-server').value = currentSettings.smtp.server || '';
  document.getElementById('smtp-port').value = currentSettings.smtp.port || 587;
  document.getElementById('smtp-username').value = currentSettings.smtp.username || '';
  document.getElementById('smtp-password').value = currentSettings.smtp.password || '';
  document.getElementById('smtp-from-email').value = currentSettings.smtp.from_email || '';
  document.getElementById('smtp-use-tls').value = currentSettings.smtp.use_tls ? 'true' : 'false';
  updateSmtpFieldVisibility();

  // Jump server settings
  document.getElementById('jump-host').value = currentSettings.jump.host || '';
  document.getElementById('jump-port').value = currentSettings.jump.port || 22;
  document.getElementById('jump-username').value = currentSettings.jump.username || '';
  document.getElementById('jump-password').value = currentSettings.jump.password || '';

  // Notification settings
  document.getElementById('notify-link-up').checked = currentSettings.notifications.link_up || false;
  document.getElementById('notify-link-down').checked = currentSettings.notifications.link_down || false;
  document.getElementById('notify-high-util').checked = currentSettings.notifications.high_utilization || false;
  document.getElementById('notify-system-error').checked = currentSettings.notifications.system_error || false;
}

// Save settings
async function saveSettings() {
  const smtpEnabled = document.getElementById('smtp-enabled').checked;
  const settingsData = {
    app: {
      ping_interval_seconds: parseInt(document.getElementById('ping-interval').value),
      session_timeout_minutes: parseInt(document.getElementById('session-timeout').value)
    },
    smtp: {
      enabled: smtpEnabled,
      server: document.getElementById('smtp-server').value.trim(),
      port: parseInt(document.getElementById('smtp-port').value),
      username: document.getElementById('smtp-username').value.trim(),
      password: document.getElementById('smtp-password').value,
      from_email: document.getElementById('smtp-from-email').value.trim(),
      use_tls: document.getElementById('smtp-use-tls').value === 'true'
    },
    jump: {
      host: document.getElementById('jump-host').value.trim(),
      port: parseInt(document.getElementById('jump-port').value),
      username: document.getElementById('jump-username').value.trim(),
      password: document.getElementById('jump-password').value
    },
    notifications: {
      link_up: document.getElementById('notify-link-up').checked,
      link_down: document.getElementById('notify-link-down').checked,
      high_utilization: document.getElementById('notify-high-util').checked,
      system_error: document.getElementById('notify-system-error').checked
    }
  };

  window.setButtonLoading(btnSaveSettings, true, 'SAVING...');

  try {
    await Promise.all([
      window.fetchAPI('/api/settings/app', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData.app)
      }),
      window.fetchAPI('/api/settings/smtp', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData.smtp)
      }),
      window.fetchAPI('/api/settings/jumpserver', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData.jump)
      }),
      window.fetchAPI('/api/notifications/subscriptions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settingsData.notifications)
      })
    ]);

    window.showToast('Settings saved successfully', 'success');
    hideSettingsModal();
  } catch (error) {
    console.error("Failed to save settings", error);
    window.showToast('Failed to save settings: ' + error.message, 'error');
  } finally {
    window.setButtonLoading(btnSaveSettings, false);
  }
}

// Update visibility of SMTP fields based on enabled checkbox
function updateSmtpFieldVisibility() {
  const enabled = document.getElementById('smtp-enabled').checked;
  document.querySelectorAll('.smtp-field').forEach(field => {
    field.classList.toggle('hidden', !enabled);
  });
}

// Test SMTP connection
async function testSmtp() {
  if (!document.getElementById('smtp-enabled').checked) {
    await window.showAlert({
      title: 'SMTP Disabled',
      message: 'SMTP is currently disabled. Enable it before testing.',
      type: 'warning'
    });
    return;
  }

  const smtpData = {
    server: document.getElementById('smtp-server').value.trim(),
    port: parseInt(document.getElementById('smtp-port').value),
    username: document.getElementById('smtp-username').value.trim(),
    password: document.getElementById('smtp-password').value,
    from_email: document.getElementById('smtp-from-email').value.trim(),
    use_tls: document.getElementById('smtp-use-tls').value === 'true'
  };

  window.setButtonLoading(btnTestSmtp, true, 'TESTING...');

  try {
    const result = await window.fetchAPI('/api/settings/smtp/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(smtpData)
    });

    window.showToast('SMTP test successful! Email sent.', 'success');
  } catch (error) {
    console.error("SMTP test failed", error);
    window.showToast('SMTP test failed: ' + error.message, 'error');
  } finally {
    window.setButtonLoading(btnTestSmtp, false);
  }
}

// Test jump server connection
async function testJumpserver() {
  const jumpData = {
    host: document.getElementById('jump-host').value.trim(),
    port: parseInt(document.getElementById('jump-port').value),
    username: document.getElementById('jump-username').value.trim(),
    password: document.getElementById('jump-password').value
  };

  window.setButtonLoading(btnTestJumpserver, true, 'TESTING...');

  try {
    const result = await window.fetchAPI('/api/settings/jumpserver/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(jumpData)
    });

    window.showToast('Jump server connection successful!', 'success');
  } catch (error) {
    console.error("Jump server test failed", error);
    window.showToast('Jump server test failed: ' + error.message, 'error');
  } finally {
    window.setButtonLoading(btnTestJumpserver, false);
  }
}

// Switch tabs
function switchTab(tabName) {
  tabButtons.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  tabPanes.forEach(pane => {
    pane.classList.toggle('active', pane.dataset.tab === tabName);
  });
}

// Show settings modal
function showSettingsModal() {
  settingsModal.classList.add('active');
  loadSettings();
}

// Hide settings modal
function hideSettingsModal() {
  settingsModal.classList.remove('active');
}

// Event listeners
settingsBtn.addEventListener('click', showSettingsModal);
btnCloseSettings.addEventListener('click', hideSettingsModal);
btnCancelSettings.addEventListener('click', hideSettingsModal);
btnSaveSettings.addEventListener('click', saveSettings);
btnTestSmtp.addEventListener('click', testSmtp);
btnTestJumpserver.addEventListener('click', testJumpserver);
document.getElementById('smtp-enabled').addEventListener('change', updateSmtpFieldVisibility);

// Tab switching
tabButtons.forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// Close on backdrop click
settingsModal.addEventListener('click', (e) => {
  if (e.target === settingsModal) hideSettingsModal();
});