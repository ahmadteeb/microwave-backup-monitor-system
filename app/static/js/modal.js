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

// Attachment Elements & State
const attachmentDropzone = document.getElementById('attachment-dropzone');
const attachmentInput = document.getElementById('modal-attachment-input');
const existingAttachmentsContainer = document.getElementById('modal-existing-attachments');
const stagedAttachmentsContainer = document.getElementById('modal-staged-attachments');
let stagedFiles = [];
let currentLinkAttachments = [];

const ALLOWED_EXTENSIONS = ['.pdf', '.vsd', '.vsdx', '.vssx', '.vstx'];

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return isoStr;
  }
}

const attachmentHelper = document.getElementById('modal-attachment-helper');

function updateAttachmentVisibility() {
  const hasExisting = currentLinkAttachments && currentLinkAttachments.length > 0;
  const hasStaged = stagedFiles && stagedFiles.length > 0;
  
  if (attachmentDropzone) {
    if (hasExisting || hasStaged) {
      attachmentDropzone.style.display = 'none';
    } else {
      attachmentDropzone.style.display = 'block';
    }
  }
}

function showAttachmentError(msg) {
  if (attachmentHelper) {
    attachmentHelper.textContent = msg;
    attachmentHelper.classList.add('error');
  }
  if (attachmentDropzone) {
    attachmentDropzone.classList.add('error');
  }
  window.showToast(msg, 'error');
}

function clearAttachmentError() {
  if (attachmentHelper) {
    attachmentHelper.textContent = 'Required field: Each link must have a Visio (.vsd, .vsdx) or PDF diagram attached.';
    attachmentHelper.classList.remove('error');
  }
  if (attachmentDropzone) {
    attachmentDropzone.classList.remove('error');
  }
}

function renderExistingAttachments(attachments, linkId) {
  currentLinkAttachments = attachments || [];
  if (!existingAttachmentsContainer) return;

  if (currentLinkAttachments.length === 0) {
    existingAttachmentsContainer.innerHTML = '';
    existingAttachmentsContainer.style.display = 'none';
    updateAttachmentVisibility();
    return;
  }

  existingAttachmentsContainer.style.display = 'flex';
  existingAttachmentsContainer.innerHTML = '';

  const att = currentLinkAttachments[0];
  const isPdf = att.is_pdf || att.filename.toLowerCase().endsWith('.pdf');
  const isVisio = att.is_visio || att.filename.toLowerCase().endsWith('.vsd') || att.filename.toLowerCase().endsWith('.vsdx');
  
  const iconClass = isPdf ? 'fa-solid fa-file-pdf text-danger' : (isVisio ? 'fa-solid fa-diagram-project text-teal' : 'fa-solid fa-file');
  const typeLabel = isPdf ? 'PDF Document' : (isVisio ? 'Visio Diagram' : 'Attachment');
  const typeBadgeClass = isPdf ? 'badge-pdf' : (isVisio ? 'badge-visio' : 'badge-file');

  const item = document.createElement('div');
  item.className = 'attachment-card';
  const safeName = window.escapeHtml ? window.escapeHtml(att.filename) : att.filename;
  item.innerHTML = `
    <div class="attachment-icon-wrapper">
      <i class="${iconClass}"></i>
    </div>
    <div class="attachment-info">
      <div class="attachment-title" title="${safeName}">${safeName}</div>
      <div class="attachment-submeta">
        <span class="attachment-type-badge ${typeBadgeClass}">${typeLabel}</span>
        <span class="attachment-size">${formatFileSize(att.file_size)}</span>
        <span class="attachment-date">${formatDate(att.uploaded_at)}</span>
      </div>
    </div>
    <div class="attachment-btn-group">
      ${isPdf ? `<a href="${window.APP_PREFIX || ''}/api/links/${linkId}/attachments/${att.id}/download?view=1" target="_blank" class="attachment-action-btn view-btn" title="Preview PDF in new tab"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>` : ''}
      <a href="${window.APP_PREFIX || ''}/api/links/${linkId}/attachments/${att.id}/download" download="${att.filename}" class="attachment-action-btn download-btn" title="Download file"><i class="fa-solid fa-download"></i></a>
      <button type="button" class="attachment-action-btn delete-btn" title="Delete attachment" data-id="${att.id}"><i class="fa-solid fa-trash-can"></i></button>
    </div>
  `;

  const deleteBtn = item.querySelector('.delete-btn');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => handleDeleteAttachment(linkId, att.id, att.filename));
  }

  existingAttachmentsContainer.appendChild(item);
  clearAttachmentError();
  updateAttachmentVisibility();
}

function renderStagedAttachments() {
  if (!stagedAttachmentsContainer) return;
  if (stagedFiles.length === 0) {
    stagedAttachmentsContainer.innerHTML = '';
    stagedAttachmentsContainer.style.display = 'none';
    updateAttachmentVisibility();
    return;
  }

  stagedAttachmentsContainer.style.display = 'flex';
  stagedAttachmentsContainer.innerHTML = '<div class="staged-header"><i class="fa-solid fa-paperclip"></i> Staged diagram for upload upon saving:</div>';

  stagedFiles.forEach((file, idx) => {
    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const isVisio = file.name.toLowerCase().endsWith('.vsd') || file.name.toLowerCase().endsWith('.vsdx');
    const iconClass = isPdf ? 'fa-solid fa-file-pdf text-danger' : (isVisio ? 'fa-solid fa-diagram-project text-teal' : 'fa-solid fa-file');

    const item = document.createElement('div');
    item.className = 'staged-file-item';
    item.innerHTML = `
      <div class="staged-file-left">
        <i class="${iconClass}"></i>
        <span class="staged-file-name" title="${file.name}">${file.name}</span>
        <span class="staged-file-size">(${formatFileSize(file.size)})</span>
      </div>
      <button type="button" class="staged-file-remove" data-index="${idx}" title="Remove staged file"><i class="fa-solid fa-xmark"></i></button>
    `;

    item.querySelector('.staged-file-remove').addEventListener('click', () => {
      stagedFiles = [];
      renderStagedAttachments();
    });

    stagedAttachmentsContainer.appendChild(item);
  });
  clearAttachmentError();
  updateAttachmentVisibility();
}

function addFilesToStaged(files) {
  if (!files || files.length === 0) return;
  const file = files[0];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    window.showToast(`File type not allowed for ${file.name}. Allowed: PDF (.pdf) and Visio (.vsd, .vsdx)`, 'error');
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    window.showToast(`File ${file.name} exceeds 50MB maximum size limit.`, 'error');
    return;
  }
  stagedFiles = [file];
  renderStagedAttachments();
}

async function handleDeleteAttachment(linkId, attachmentId, filename) {
  const confirmed = await window.showConfirm({
    title: 'DELETE ATTACHMENT',
    message: `Are you sure you want to delete attachment <strong>${window.escapeHtml ? window.escapeHtml(filename) : filename}</strong>?`,
    confirmText: 'DELETE',
    cancelText: 'CANCEL',
    variant: 'danger'
  });

  if (!confirmed) return;

  const loader = window.showLoading('Deleting attachment...');
  try {
    const res = await window.fetchAPI(`/api/links/${linkId}/attachments/${attachmentId}`, {
      method: 'DELETE'
    });
    loader.close();
    window.showToast('Attachment deleted successfully', 'success');
    currentLinkAttachments = (res.link && res.link.attachments) ? res.link.attachments : [];
    renderExistingAttachments(currentLinkAttachments, linkId);
    if (window.refreshTable) window.refreshTable();
  } catch (err) {
    loader.close();
    window.showToast('Failed to delete attachment: ' + err.message, 'error');
  }
}

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
    inputWarningThresh.value = data.util_warning_threshold_pct !== null && data.util_warning_threshold_pct !== undefined ? data.util_warning_threshold_pct : '';
    inputCriticalThresh.value = data.util_critical_threshold_pct !== null && data.util_critical_threshold_pct !== undefined ? data.util_critical_threshold_pct : '';
    renderExistingAttachments(data.attachments || [], data.id);
  } else {
    renderExistingAttachments([], null);
  }
  
  modalOverlay.classList.add('active');
}

function closeModal() {
  modalOverlay.classList.remove('active');
  stagedFiles = [];
  renderStagedAttachments();
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
  stagedFiles = [];
  if (attachmentInput) attachmentInput.value = '';
  renderStagedAttachments();
  renderExistingAttachments([], null);
  resetMetricFields();
  clearExternalLookup();
  clearAttachmentError();
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

  const hasExisting = currentLinkAttachments && currentLinkAttachments.length > 0;
  const hasStaged = stagedFiles && stagedFiles.length > 0;
  if (!hasExisting && !hasStaged) {
    showAttachmentError('Link diagram attachment is required. Please attach a Visio (.vsd, .vsdx) or PDF file.');
    return;
  }

  
  const id = modalId.value;
  const isEdit = id !== '';
  const url = isEdit ? `/api/links/${id}` : '/api/links';
  const method = isEdit ? 'PUT' : 'POST';
  
  // Show loading state on save button
  window.setButtonLoading(btnSaveModal, true, 'SAVING...');
  
  try {
    let response;
    if (stagedFiles.length > 0) {
      // Use FormData for multipart submission including files
      const formData = new FormData();
      formData.append('link_id', linkId);
      formData.append('leg_name', legName);
      formData.append('site_a', siteA);
      formData.append('site_b', siteB);
      formData.append('mw_ip', mwIp);
      if (warningThresh !== null) formData.append('util_warning_threshold_pct', warningThresh);
      if (criticalThresh !== null) formData.append('util_critical_threshold_pct', criticalThresh);

      stagedFiles.forEach(file => {
        formData.append('attachments', file);
      });

      const res = await fetch((window.APP_PREFIX || '') + url, {
        method: method,
        body: formData
      });
      response = await res.json();
      if (!res.ok) {
        throw new Error(response.error || 'Failed to save link');
      }
    } else {
      // Standard JSON submission
      const payload = {
        link_id: linkId,
        leg_name: legName,
        site_a: siteA,
        site_b: siteB,
        mw_ip: mwIp,
        util_warning_threshold_pct: warningThresh,
        util_critical_threshold_pct: criticalThresh
      };

      response = await window.fetchAPI(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    
    stagedFiles = [];
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

// Attachment Dropzone Event Listeners
if (attachmentDropzone) {
  attachmentDropzone.addEventListener('click', () => {
    if (attachmentInput) attachmentInput.click();
  });

  attachmentDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    attachmentDropzone.classList.add('drag-active');
  });

  attachmentDropzone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    attachmentDropzone.classList.remove('drag-active');
  });

  attachmentDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    attachmentDropzone.classList.remove('drag-active');
    if (e.dataTransfer && e.dataTransfer.files) {
      addFilesToStaged(e.dataTransfer.files);
    }
  });
}

if (attachmentInput) {
  attachmentInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFilesToStaged(e.target.files);
      attachmentInput.value = '';
    }
  });
}

// Close on backdrop click
modalOverlay.addEventListener('click', (e) => {
  if (e.target === modalOverlay) closeModal();
});

// Bulk Add Logic
const btnBulkAdd = document.getElementById('btn-bulk-add');
const bulkAddModal = document.getElementById('bulk-add-modal');
const btnCloseBulkModal = document.getElementById('btn-close-bulk-modal');
const btnCancelBulkModal = document.getElementById('btn-cancel-bulk-modal');
const btnSubmitBulkModal = document.getElementById('btn-submit-bulk-modal');
const bulkUploadFile = document.getElementById('bulk-upload-file');
const bulkAddResults = document.getElementById('bulk-add-results');

function openBulkModal() {
  if (bulkUploadFile) bulkUploadFile.value = '';
  if (bulkAddResults) {
    bulkAddResults.innerHTML = '';
    bulkAddResults.classList.add('hidden');
  }
  if (bulkAddModal) {
    bulkAddModal.classList.remove('hidden');
    bulkAddModal.classList.add('active');
  }
}

function closeBulkModal() {
  if (bulkAddModal) {
    bulkAddModal.classList.remove('active');
  }
}

if (btnBulkAdd) {
  btnBulkAdd.addEventListener('click', openBulkModal);
}

if (btnCloseBulkModal) {
  btnCloseBulkModal.addEventListener('click', closeBulkModal);
}

if (btnCancelBulkModal) {
  btnCancelBulkModal.addEventListener('click', closeBulkModal);
}

if (bulkAddModal) {
  bulkAddModal.addEventListener('click', (e) => {
    if (e.target === bulkAddModal) closeBulkModal();
  });
}

if (btnSubmitBulkModal) {
  btnSubmitBulkModal.addEventListener('click', async () => {
    if (!bulkUploadFile || !bulkUploadFile.files || bulkUploadFile.files.length === 0) {
      window.showToast('Please select a file to upload.', 'error');
      return;
    }

    const file = bulkUploadFile.files[0];
    const formData = new FormData();
    formData.append('file', file);

    window.setButtonLoading(btnSubmitBulkModal, true, 'UPLOADING...');
    if (bulkAddResults) {
      bulkAddResults.innerHTML = '';
      bulkAddResults.className = 'hidden';
    }

    try {
      // Direct fetch to handle multipart/form-data
      const response = await fetch(window.APP_PREFIX + '/api/links/bulk', {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header, let browser boundary handle it
        headers: {
          // If you have auth tokens, add them here
        }
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Upload failed');
      }

      window.showToast(data.message, 'success');
      
      // Show results
      if (bulkAddResults) {
        bulkAddResults.classList.remove('hidden');
        let html = `<div style="color: var(--status-up); margin-bottom: 8px;">Success: ${data.success_count} links added.</div>`;
        if (data.failed_count > 0) {
          html += `<div style="color: var(--status-down); font-weight: bold; margin-bottom: 4px;">Failed rows (${data.failed_count}):</div>`;
          html += `<ul style="color: var(--status-down); margin: 0; padding-left: 20px; max-height: 150px; overflow-y: auto;">`;
          data.failures.forEach(f => {
            html += `<li>Row ${f.row}: ${f.reason}</li>`;
          });
          html += `</ul>`;
        }
        bulkAddResults.innerHTML = html;
      }
      
      if (window.refreshTable && data.success_count > 0) {
        window.refreshTable();
      }
      
    } catch (err) {
      window.showToast('Upload error: ' + err.message, 'error');
      if (bulkAddResults) {
        bulkAddResults.classList.remove('hidden');
        bulkAddResults.innerHTML = `<div style="color: var(--status-down);">Error: ${err.message}</div>`;
      }
    } finally {
      window.setButtonLoading(btnSubmitBulkModal, false);
      if (bulkUploadFile) bulkUploadFile.value = '';
    }
  });
}
