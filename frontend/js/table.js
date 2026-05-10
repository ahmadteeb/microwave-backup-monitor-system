// DOM Elements
const tableBody = document.getElementById('link-table-body');
const searchInput = document.getElementById('search-input');
const statusFilter = document.getElementById('status-filter');
const legFilter = document.getElementById('leg-filter');
const btnTableDownload = document.getElementById('btn-table-download');
const btnPrevPage = document.getElementById('btn-prev-page');
const btnNextPage = document.getElementById('btn-next-page');
const pageInfo = document.getElementById('page-info');
const tableCount = document.getElementById('table-count');

// State
let currentPage = 1;
let totalPages = 1;
let searchTimeout = null;

// API Fetch
async function pollTable() {
  const status = statusFilter.value;
  const leg = legFilter.value;
  const search = searchInput.value.trim();
  
  let url = `/api/links?page=${currentPage}&per_page=10`; // using 10 for v1 display purposes
  if (status && status !== 'ALL_OPERATIONAL') url += `&status=${status}`;
  if (leg && leg !== 'ALL_REGIONS') url += `&leg=${leg}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const data = await window.fetchAPI(url);
    renderTable(data.links);
    updatePagination(data);
  } catch (error) {
    console.error("Failed to fetch table data", error);
  }
}

// In-place row update from WebSocket event
function handleLinkStatusUpdate(update) {
  // Try to update the matching row in-place without a full re-fetch
  const rows = tableBody.querySelectorAll('tr');
  for (const row of rows) {
    const linkIdCell = row.querySelector('td:first-child');
    if (linkIdCell && linkIdCell.textContent === update.link_id) {
      // Update status badge
      const statusCell = row.querySelector('.status-badge');
      if (statusCell) {
        statusCell.className = `status-badge ${update.status.toLowerCase()}`;
        statusCell.textContent = update.status;
      }

      // Update latency
      const latencyCell = row.querySelector('td:nth-child(6)');
      if (latencyCell) {
        latencyCell.innerHTML = update.latency_ms !== null
          ? `<span class="text-teal">${update.latency_ms}ms</span>`
          : `<span class="text-muted">—</span>`;
      }

      // Update utilization bars
      if (update.latest_metric) {
        const fiberCell = row.querySelector('td:nth-child(3)');
        const mwCell = row.querySelector('td:nth-child(4)');
        if (fiberCell) {
          const fiberPct = update.latest_metric.fiber_util_pct ?? 0;
          fiberCell.innerHTML = createUtilBar(fiberPct, getBarColor(fiberPct));
        }
        if (mwCell) {
          const mwPct = update.latest_metric.mw_util_pct ?? 0;
          mwCell.innerHTML = createUtilBar(mwPct, getBarColor(mwPct));
        }
      }

      // Flash animation for the updated row
      row.style.transition = 'background 0.3s';
      row.style.background = 'rgba(0, 212, 170, 0.08)';
      setTimeout(() => {
        row.style.background = '';
      }, 1500);

      return; // Found and updated
    }
  }
  // If the link isn't on the current page, do nothing
}

// Rendering
function renderTable(links) {
  tableBody.innerHTML = '';

  if (links.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No links found matching criteria.</td></tr>`;
    return;
  }

  links.forEach(link => {
    const tr = document.createElement('tr');

    const fiberPct = link.latest_metric && link.latest_metric.fiber_util_pct !== null ? link.latest_metric.fiber_util_pct : 0;
    const fiberColor = getBarColor(fiberPct);
    const fiberBar = createUtilBar(fiberPct, fiberColor);

    const mwPct = link.latest_metric && link.latest_metric.mw_util_pct !== null ? link.latest_metric.mw_util_pct : 0;
    const mwColor = getBarColor(mwPct);
    const mwBar = createUtilBar(mwPct, mwColor);

    const statusHtml = `<span class="status-badge ${link.status.toLowerCase()}">${link.status}</span>`;

    const latencyHtml = link.latency_ms !== null 
      ? `<span class="text-teal">${link.latency_ms}ms</span>` 
      : `<span class="text-muted">—</span>`;

    tr.innerHTML = `
      <td class="text-mono text-teal">${link.link_id}</td>
      <td>${link.leg_name}</td>
      <td>${fiberBar}</td>
      <td>${mwBar}</td>
      <td>${statusHtml}</td>
      <td class="text-mono">${latencyHtml}</td>
    `;

    const actionCell = document.createElement('td');
    actionCell.className = 'action-btns';
    actionCell.style.textAlign = 'right';

    const editBtn = document.createElement('i');
    editBtn.className = 'fa-solid fa-pencil';
    editBtn.title = 'Edit Link';
    editBtn.style.cursor = 'pointer';
    editBtn.addEventListener('click', () => window.openEditModal(link.id));

    const deleteBtn = document.createElement('i');
    deleteBtn.className = 'fa-solid fa-trash-can';
    deleteBtn.title = 'Delete Link';
    deleteBtn.style.cursor = 'pointer';
    deleteBtn.addEventListener('click', () => window.deleteLink(link.id, link.link_id));

    actionCell.appendChild(editBtn);
    actionCell.appendChild(deleteBtn);
    tr.appendChild(actionCell);

    tableBody.appendChild(tr);
  });
}

function createUtilBar(pct, colorVar) {
  return `
    <div class="util-bar-container">
      <div class="util-pct">${Math.round(pct)}%</div>
      <div class="util-bar-track">
        <div class="util-bar-fill" style="width: ${pct}%; background-color: var(${colorVar});"></div>
      </div>
    </div>
  `;
}

function getBarColor(pct) {
  if (pct >= 90) return '--bar-critical';
  if (pct >= 70) return '--bar-warning';
  return '--bar-optimal';
}

function updatePagination(data) {
  currentPage = data.page;
  totalPages = data.pages;
  
  pageInfo.textContent = `PAGE ${currentPage} OF ${Math.max(1, totalPages)}`;
  tableCount.textContent = `${data.total} TOTAL`;
  
  btnPrevPage.disabled = currentPage <= 1;
  btnNextPage.disabled = currentPage >= totalPages;
}

async function loadLegOptions() {
  try {
    const data = await window.fetchAPI('/api/links/legs');
    legFilter.innerHTML = '<option value="ALL_REGIONS">All regions</option>';
    (data.legs || []).forEach((leg) => {
      const option = document.createElement('option');
      option.value = leg;
      option.textContent = leg;
      legFilter.appendChild(option);
    });
  } catch (e) {
    console.warn('Failed to load leg options', e);
  }
}

// Event Listeners
searchInput.addEventListener('input', () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentPage = 1;
    pollTable();
  }, 300);
});

statusFilter.addEventListener('change', () => {
  currentPage = 1;
  pollTable();
});

legFilter.addEventListener('change', () => {
  currentPage = 1;
  pollTable();
});

if (btnTableDownload) {
  btnTableDownload.addEventListener('click', () => {
    const params = new URLSearchParams();
    if (statusFilter.value && statusFilter.value !== 'ALL_OPERATIONAL') {
      params.set('status', statusFilter.value);
    }
    if (legFilter.value && legFilter.value !== 'ALL_REGIONS') {
      params.set('leg', legFilter.value);
    }
    const search = searchInput.value.trim();
    if (search) {
      params.set('search', search);
    }
    window.location.href = `/api/links/export?${params.toString()}`;
  });
}

btnPrevPage.addEventListener('click', () => {
  if (currentPage > 1) {
    currentPage--;
    pollTable();
  }
});

btnNextPage.addEventListener('click', () => {
  if (currentPage < totalPages) {
    currentPage++;
    pollTable();
  }
});

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadLegOptions();
  pollTable();

  // Listen for real-time link status updates via WebSocket
  window.addEventListener('ws:link_status_update', (event) => {
    handleLinkStatusUpdate(event.detail);
  });

  // Expose pollTable for modal.js to call after CRUD
  window.refreshTable = pollTable;
});
