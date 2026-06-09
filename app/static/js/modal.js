// DOM Elements
const modalOverlay = document.getElementById('link-modal');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnCancelModal = document.getElementById('btn-cancel-modal');
const btnSaveModal = document.getElementById('btn-save-modal');
const btnAddLink = document.getElementById('btn-add-link');

// Form Fields
const modalId = document.getElementById('modal-id');
const inputLinkId = document.getElementById('modal-link-id');
const inputLegName = document.getElementById('modal-leg-name');
const inputSiteA = document.getElementById('modal-site-a');
const inputSiteB = document.getElementById('modal-site-b');
const inputMwIp = document.getElementById('modal-mw-ip');
const inputWarningThresh = document.getElementById('modal-warning-thresh');
const inputCriticalThresh = document.getElementById('modal-critical-thresh');
const ipHelper = document.getElementById('modal-ip-helper');
const ipErrorIcon = document.getElementById('ip-error-icon');
const btnFetchLinkInfo = document.getElementById('btn-fetch-link-info');
const btnFetchLegInfo = document.getElementById('btn-fetch-leg-info');
const externalLookupSection = document.getElementById('external-lookup-section');
const externalLinkDetails = document.getElementById('external-link-details');
const externalLegDetails = document.getElementById('external-leg-details');
// Record utilization elements removed from modal UI

// Functions
function openModal(mode = 'create', data = {}) {
  resetForm();
  clearExternalLookup();

  if (mode === 'edit') {
    modalId.value = data.id;
    inputLinkId.value = data.link_id;
    inputLegName.value = data.leg_name;
    inputSiteA.value = data.site_a || '';
    inputSiteB.value = data.site_b || '';
    inputMwIp.value = data.mw_ip;
    inputWarningThresh.value = data.util_warning_threshold_pct !== null ? data.util_warning_threshold_pct : '';
    inputCriticalThresh.value = data.util_critical_threshold_pct !== null ? data.util_critical_threshold_pct : '';
    // Record utilization UI removed
  } else {
    // Create mode: no record utilization UI
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
  inputWarningThresh.value = '';
  inputCriticalThresh.value = '';
  resetMetricFields();
  clearExternalLookup();
  inputMwIp.classList.remove('error');
  ipHelper.classList.remove('error');
  ipErrorIcon.classList.add('hidden');
  ipHelper.textContent = 'Required field: Provide a valid IPv4 address for link telemetry.';
}

function resetMetricFields() {
  // Metric fields removed; no-op
}

function clearExternalLookup() {
  if (externalLookupSection) {
    externalLookupSection.style.display = 'none';
  }
  if (externalLinkDetails) {
    externalLinkDetails.innerHTML = '';
  }
  if (externalLegDetails) {
    externalLegDetails.innerHTML = '';
  }
}

function renderLookupDetail(title, value) {
  return `<div class="lookup-detail"><strong>${title}:</strong> ${value !== null && value !== undefined ? value : 'N/A'}</div>`;
}

function showMetricError(msg) {
  if (metricMessage) {
    metricMessage.textContent = msg;
    metricMessage.classList.add('error');
  }
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
  const warningThresh = inputWarningThresh.value ? parseInt(inputWarningThresh.value, 10) : null;
  const criticalThresh = inputCriticalThresh.value ? parseInt(inputCriticalThresh.value, 10) : null;
  
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
    mw_ip: mwIp,
    util_warning_threshold_pct: warningThresh,
    util_critical_threshold_pct: criticalThresh
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

async function handleFetchLinkInfo() {
  const linkId = inputLinkId.value.trim();
  if (!linkId) {
    window.showToast('Enter a Link ID first to fetch external data.', 'error');
    return;
  }

  window.setButtonLoading(btnFetchLinkInfo, true, 'FETCHING...');
  try {
    const response = await window.fetchAPI('/api/links/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ link_id: linkId })
    });

    inputSiteA.value = response.external.Source_NE_Card || inputSiteA.value;
    inputSiteB.value = response.external.Sink_NE_Card || inputSiteB.value;

    if (externalLookupSection) {
      externalLookupSection.style.display = 'block';
    }
    if (externalLinkDetails) {
      externalLinkDetails.innerHTML = '';
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('External Link Name', response.external.Link_Name));
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Link Unif', response.external.Link_Name_Unif));
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Link Category', response.external.Link_Categ));
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Average MW Util %', response.external.AVG_MAX_Util_RxTx_perc));
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Avg Rx Kbps', response.external.AVG_MAX_Rx_Kbps));
      externalLinkDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Avg Tx Kbps', response.external.AVG_MAX_Tx_Kbps));
    }
    // If editing an existing link, record the external MW utilization so the table updates immediately
    const id = modalId.value;
    if (id) {
      const extUtil = parseFloat(response.external.AVG_MAX_Util_RxTx_perc);
      if (!Number.isNaN(extUtil)) {
        try {
          await window.fetchAPI(`/api/links/${id}/metrics`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mw_util_pct: extUtil, source: 'external' })
          });
          if (window.refreshTable) window.refreshTable();
        } catch (err) {
          console.warn('Failed to persist external utilization', err);
        }
      }
    }
  } catch (err) {
    window.showToast('Failed to fetch external link information: ' + err.message, 'error');
  } finally {
    window.setButtonLoading(btnFetchLinkInfo, false);
  }
}

async function handleFetchLegInfo() {
  const legName = inputLegName.value.trim();
  if (!legName) {
    window.showToast('Enter a LEG name first to fetch external data.', 'error');
    return;
  }

  window.setButtonLoading(btnFetchLegInfo, true, 'FETCHING...');
  try {
    const response = await window.fetchAPI('/api/links/lookup-leg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leg_name: legName })
    });

    if (externalLookupSection) {
      externalLookupSection.style.display = 'block';
    }
    if (externalLegDetails) {
      externalLegDetails.innerHTML = '';
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('LEG Name', response.external.LEG_Name));
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Average Max MBitRate', response.external.AVG_MAX_MBitRate));
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Interface Speed Min', response.external.Interface_Speed_Min));
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Interface Speed Max', response.external.Interface_Speed_Max));
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('LEG Util %', response.external.LEG_Util_pct !== null && response.external.LEG_Util_pct !== undefined ? `${response.external.LEG_Util_pct}%` : 'N/A'));
      externalLegDetails.insertAdjacentHTML('beforeend', renderLookupDetail('Sub LEG Count', response.external.Sub_LEG_Count));
    }
  } catch (err) {
    window.showToast('Failed to fetch external LEG information: ' + err.message, 'error');
  } finally {
    window.setButtonLoading(btnFetchLegInfo, false);
  }
}

// Record utilization UI removed; persistence of external metrics still occurs when fetching link info for edits.

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
if (btnAddLink) {
  btnAddLink.addEventListener('click', () => openModal('create'));
}
btnCloseModal.addEventListener('click', closeModal);
btnCancelModal.addEventListener('click', closeModal);
btnSaveModal.addEventListener('click', handleSave);
if (btnFetchLinkInfo) {
  btnFetchLinkInfo.addEventListener('click', handleFetchLinkInfo);
}
if (btnFetchLegInfo) {
  btnFetchLegInfo.addEventListener('click', handleFetchLegInfo);
}
// submit metric button removed

// Close on backdrop click
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});
