// DOM Elements
const modalOverlay = document.getElementById('link-modal');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnCancelModal = document.getElementById('btn-cancel-modal');
const btnSaveModal = document.getElementById('btn-save-modal');
const btnAddSidebar = document.getElementById('btn-add-sidebar');
const fabAddLink = document.getElementById('fab-add-link');

// Form Fields
const modalId = document.getElementById('modal-id');
const inputLinkId = document.getElementById('modal-link-id');
const inputLegName = document.getElementById('modal-leg-name');
const inputSiteA = document.getElementById('modal-site-a');
const inputSiteB = document.getElementById('modal-site-b');
const inputMwIp = document.getElementById('modal-mw-ip');
const ipHelper = document.getElementById('modal-ip-helper');
const ipErrorIcon = document.getElementById('ip-error-icon');

// Functions
function openModal(mode = 'create', data = {}) {
  resetForm();
  
  if (mode === 'edit') {
    modalId.value = data.id;
    inputLinkId.value = data.link_id;
    inputLegName.value = data.leg_name;
    inputSiteA.value = data.site_a || '';
    inputSiteB.value = data.site_b || '';
    inputMwIp.value = data.mw_ip;
  }
  
  modalOverlay.classList.add('active');
}

function closeModal() {
  modalOverlay.classList.remove('active');
}

function resetForm() {
  modalId.value = '';
  inputLinkId.value = '';
  inputLegName.value = '';
  inputSiteA.value = '';
  inputSiteB.value = '';
  inputMwIp.value = '';
  
  inputMwIp.classList.remove('error');
  ipHelper.classList.remove('error');
  ipErrorIcon.classList.add('hidden');
  ipHelper.textContent = 'Required field: Provide a valid IPv4 address for link telemetry.';
}

function validateIPv4(ip) {
  const regex = /^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$/;
  return regex.test(ip);
}

function showError(msg) {
  inputMwIp.classList.add('error');
  ipHelper.classList.add('error');
  ipErrorIcon.classList.remove('hidden');
  ipHelper.textContent = msg;
}

async function handleSave() {
  const linkId = inputLinkId.value.trim();
  const legName = inputLegName.value.trim();
  const siteA = inputSiteA.value.trim();
  const siteB = inputSiteB.value.trim();
  const mwIp = inputMwIp.value.trim();
  
  if (!linkId || !legName || !mwIp) {
    showError('LINK_ID, LEG_NAME, and MW_IP are required.');
    return;
  }
  
  if (!validateIPv4(mwIp)) {
    showError('Invalid IPv4 address format.');
    return;
  }
  
  const payload = {
    link_id: linkId,
    leg_name: legName,
    site_a: siteA,
    site_b: siteB,
    mw_ip: mwIp
  };
  
  const id = modalId.value;
  const isEdit = id !== '';
  const url = isEdit ? `/api/links/${id}` : '/api/links';
  const method = isEdit ? 'PUT' : 'POST';
  
  // Show loading state on save button
  window.setButtonLoading(btnSaveModal, true, 'SAVING...');
  
  try {
    const response = await window.fetchAPI(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    closeModal();
    window.showToast(isEdit ? 'Link updated successfully' : 'Link created successfully', 'success');
    if (window.refreshTable) window.refreshTable();
  } catch (err) {
    showError(err.message);
    window.showToast('Failed to save link: ' + err.message, 'error');
  } finally {
    window.setButtonLoading(btnSaveModal, false);
  }
}

// Global functions for table actions
window.openEditModal = async (id) => {
  try {
    const data = await window.fetchAPI(`/api/links/${id}`);
    openModal('edit', data.link);
  } catch (err) {
    console.error("Failed to load link details", err);
    window.showToast('Failed to load link details', 'error');
  }
};

window.deleteLink = async (id, linkId) => {
  const confirmed = await window.showConfirm({
    title: 'DELETE LINK',
    message: `Are you sure you want to delete link <strong>${linkId}</strong>?<br>This action cannot be undone.`,
    confirmText: 'DELETE',
    cancelText: 'CANCEL',
    variant: 'danger'
  });

  if (confirmed) {
    const loader = window.showLoading('Deleting link...');
    try {
      await window.fetchAPI(`/api/links/${id}`, { method: 'DELETE' });
      loader.close();
      window.showToast(`Link ${linkId} deleted successfully`, 'success');
      if (window.refreshTable) window.refreshTable();
    } catch (err) {
      loader.close();
      console.error("Failed to delete link", err);
      window.showToast('Error deleting link: ' + err.message, 'error');
    }
  }
};

// Event Listeners
if (btnAddSidebar) {
  btnAddSidebar.addEventListener('click', () => openModal('create'));
}
if (fabAddLink) {
  fabAddLink.addEventListener('click', () => openModal('create'));
}
btnCloseModal.addEventListener('click', closeModal);
btnCancelModal.addEventListener('click', closeModal);
btnSaveModal.addEventListener('click', handleSave);

// Close on backdrop click
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});
