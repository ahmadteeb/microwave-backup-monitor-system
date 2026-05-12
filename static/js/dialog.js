/**
 * Dialog System — Premium custom dialogs replacing browser alert/confirm
 * Provides: showToast, showConfirm, showAlert, showLoading, setButtonLoading
 */

// ─── Toast Notification System ───────────────────────────────────────────────

const TOAST_DURATION = 4000;
const TOAST_ICONS = {
  success: 'fa-solid fa-circle-check',
  error: 'fa-solid fa-circle-xmark',
  warning: 'fa-solid fa-triangle-exclamation',
  info: 'fa-solid fa-circle-info'
};

function ensureToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  return container;
}

/**
 * Show a toast notification
 * @param {string} message - Toast message
 * @param {'success'|'error'|'warning'|'info'} type - Toast type
 * @param {number} duration - Auto-dismiss duration in ms
 */
function showToast(message, type = 'info', duration = TOAST_DURATION) {
  const container = ensureToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <i class="${TOAST_ICONS[type]} toast-icon"></i>
    <span class="toast-message">${message}</span>
    <button class="toast-close" aria-label="Dismiss">
      <i class="fa-solid fa-xmark"></i>
    </button>
  `;

  // Dismiss on click
  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => dismissToast(toast));
  toast.addEventListener('click', (e) => {
    if (e.target !== closeBtn && !closeBtn.contains(e.target)) {
      dismissToast(toast);
    }
  });

  container.appendChild(toast);

  // Trigger entrance animation
  requestAnimationFrame(() => {
    toast.classList.add('toast-enter');
  });

  // Auto-dismiss
  const timer = setTimeout(() => dismissToast(toast), duration);
  toast._timer = timer;
}

function dismissToast(toast) {
  if (toast._dismissed) return;
  toast._dismissed = true;
  clearTimeout(toast._timer);
  toast.classList.remove('toast-enter');
  toast.classList.add('toast-exit');
  toast.addEventListener('animationend', () => {
    toast.remove();
  }, { once: true });
  // Fallback removal
  setTimeout(() => toast.remove(), 500);
}

// ─── Dialog System (Alert & Confirm) ─────────────────────────────────────────

const DIALOG_ICONS = {
  success: { icon: 'fa-solid fa-circle-check', class: 'dialog-icon-success' },
  error: { icon: 'fa-solid fa-circle-xmark', class: 'dialog-icon-error' },
  warning: { icon: 'fa-solid fa-triangle-exclamation', class: 'dialog-icon-warning' },
  info: { icon: 'fa-solid fa-circle-info', class: 'dialog-icon-info' },
  danger: { icon: 'fa-solid fa-trash-can', class: 'dialog-icon-danger' }
};

function createDialogOverlay() {
  const overlay = document.createElement('div');
  overlay.className = 'dialog-overlay';
  document.body.appendChild(overlay);

  // Animate in
  requestAnimationFrame(() => {
    overlay.classList.add('dialog-active');
  });

  return overlay;
}

function closeDialogOverlay(overlay) {
  overlay.classList.remove('dialog-active');
  overlay.classList.add('dialog-closing');
  overlay.addEventListener('animationend', () => {
    overlay.remove();
  }, { once: true });
  // Fallback
  setTimeout(() => overlay.remove(), 400);
}

/**
 * Show a confirmation dialog
 * @param {Object} options
 * @param {string} options.title - Dialog title
 * @param {string} options.message - Dialog message
 * @param {string} options.confirmText - Confirm button text (default: 'CONFIRM')
 * @param {string} options.cancelText - Cancel button text (default: 'CANCEL')
 * @param {'danger'|'warning'|'default'} options.variant - Button variant
 * @returns {Promise<boolean>} - true if confirmed, false if cancelled
 */
function showConfirm({ title = 'Confirm Action', message = '', confirmText = 'CONFIRM', cancelText = 'CANCEL', variant = 'default' } = {}) {
  return new Promise((resolve) => {
    const overlay = createDialogOverlay();

    const iconType = variant === 'danger' ? 'danger' : variant === 'warning' ? 'warning' : 'info';
    const iconData = DIALOG_ICONS[iconType];
    const btnClass = variant === 'danger' ? 'btn-danger' : variant === 'warning' ? 'btn-warning' : 'btn-primary';

    const dialog = document.createElement('div');
    dialog.className = 'dialog-box';
    dialog.innerHTML = `
      <div class="dialog-icon-container">
        <div class="dialog-icon-circle ${iconData.class}">
          <i class="${iconData.icon}"></i>
        </div>
      </div>
      <div class="dialog-title">${title}</div>
      <div class="dialog-message">${message}</div>
      <div class="dialog-actions">
        <button class="btn-ghost dialog-cancel-btn">${cancelText}</button>
        <button class="${btnClass} dialog-confirm-btn">${confirmText}</button>
      </div>
    `;

    overlay.appendChild(dialog);

    const confirmBtn = dialog.querySelector('.dialog-confirm-btn');
    const cancelBtn = dialog.querySelector('.dialog-cancel-btn');

    const handleConfirm = () => {
      closeDialogOverlay(overlay);
      resolve(true);
    };

    const handleCancel = () => {
      closeDialogOverlay(overlay);
      resolve(false);
    };

    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);

    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) handleCancel();
    });

    // Keyboard support
    const handleKeydown = (e) => {
      if (e.key === 'Escape') {
        handleCancel();
        document.removeEventListener('keydown', handleKeydown);
      } else if (e.key === 'Enter') {
        handleConfirm();
        document.removeEventListener('keydown', handleKeydown);
      }
    };
    document.addEventListener('keydown', handleKeydown);

    // Focus confirm button
    requestAnimationFrame(() => confirmBtn.focus());
  });
}

/**
 * Show an alert dialog
 * @param {Object} options
 * @param {string} options.title - Dialog title
 * @param {string} options.message - Dialog message
 * @param {'success'|'error'|'warning'|'info'} options.type - Alert type
 * @param {string} options.buttonText - Button text (default: 'OK')
 * @returns {Promise<void>}
 */
function showAlert({ title = 'Alert', message = '', type = 'info', buttonText = 'OK' } = {}) {
  return new Promise((resolve) => {
    const overlay = createDialogOverlay();

    const iconData = DIALOG_ICONS[type] || DIALOG_ICONS.info;

    const dialog = document.createElement('div');
    dialog.className = 'dialog-box';
    dialog.innerHTML = `
      <div class="dialog-icon-container">
        <div class="dialog-icon-circle ${iconData.class}">
          <i class="${iconData.icon}"></i>
        </div>
      </div>
      <div class="dialog-title">${title}</div>
      <div class="dialog-message">${message}</div>
      <div class="dialog-actions dialog-actions-center">
        <button class="btn-primary dialog-ok-btn">${buttonText}</button>
      </div>
    `;

    overlay.appendChild(dialog);

    const okBtn = dialog.querySelector('.dialog-ok-btn');

    const handleOk = () => {
      closeDialogOverlay(overlay);
      resolve();
    };

    okBtn.addEventListener('click', handleOk);

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) handleOk();
    });

    const handleKeydown = (e) => {
      if (e.key === 'Escape' || e.key === 'Enter') {
        handleOk();
        document.removeEventListener('keydown', handleKeydown);
      }
    };
    document.addEventListener('keydown', handleKeydown);

    requestAnimationFrame(() => okBtn.focus());
  });
}

// ─── Loading Overlay ─────────────────────────────────────────────────────────

/**
 * Show a loading overlay
 * @param {string} message - Loading message
 * @returns {{ close: () => void }} - Call close() to dismiss
 */
function showLoading(message = 'Processing...') {
  const overlay = document.createElement('div');
  overlay.className = 'loading-overlay';
  overlay.innerHTML = `
    <div class="loading-dialog">
      <div class="loading-spinner">
        <div class="spinner-orbit">
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
          <div class="spinner-dot"></div>
        </div>
      </div>
      <div class="loading-message">${message}</div>
    </div>
  `;

  document.body.appendChild(overlay);

  requestAnimationFrame(() => {
    overlay.classList.add('loading-active');
  });

  return {
    close: () => {
      overlay.classList.remove('loading-active');
      overlay.classList.add('loading-closing');
      setTimeout(() => overlay.remove(), 300);
    },
    updateMessage: (newMessage) => {
      const msgEl = overlay.querySelector('.loading-message');
      if (msgEl) msgEl.textContent = newMessage;
    }
  };
}

// ─── Button Loading State ────────────────────────────────────────────────────

/**
 * Set a button to loading state
 * @param {HTMLButtonElement} btn - The button element
 * @param {boolean} loading - Whether to show loading
 * @param {string} loadingText - Text to show during loading
 */
function setButtonLoading(btn, loading, loadingText = 'Processing...') {
  if (loading) {
    btn._originalHTML = btn.innerHTML;
    btn._originalDisabled = btn.disabled;
    btn.disabled = true;
    btn.classList.add('btn-loading');
    btn.innerHTML = `<span class="btn-spinner"></span> ${loadingText}`;
  } else {
    btn.disabled = btn._originalDisabled || false;
    btn.classList.remove('btn-loading');
    if (btn._originalHTML) {
      btn.innerHTML = btn._originalHTML;
    }
  }
}

// ─── Make available globally ─────────────────────────────────────────────────

window.showToast = showToast;
window.showConfirm = showConfirm;
window.showAlert = showAlert;
window.showLoading = showLoading;
window.setButtonLoading = setButtonLoading;
