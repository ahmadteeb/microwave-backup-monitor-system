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

// Helpers
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function truncateText(s, n = 18) {
  if (!s) return '';
  return s.length > n ? s.slice(0, n) + '...' : s;
}

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
      const latencyCell = row.querySelector('td:nth-child(9)');
      if (latencyCell) {
        latencyCell.innerHTML = update.latency_ms !== null
          ? `<span class="text-teal">${update.latency_ms}ms</span>`
          : `<span class="text-muted">—</span>`;
      }

      // Update utilization bars
      if (update.latest_metric) {
        const legCell = row.querySelector('td:nth-child(5)');
        const mwCell = row.querySelector('td:nth-child(6)');
        const capCell = row.querySelector('td:nth-child(7)');
        if (legCell) {
          const legPct = update.latest_metric.leg_util_pct ?? 0;
          legCell.innerHTML = createUtilBar(legPct, getBarColor(legPct));
        }
        if (mwCell) {
          const mwPct = update.latest_metric.mw_util_pct ?? 0;
          mwCell.innerHTML = createUtilBar(mwPct, getBarColor(mwPct));
        }
        if (capCell && update.latest_metric.mw_capacity_mbps !== undefined) {
          capCell.innerHTML = formatCapacity(update.latest_metric.mw_capacity_mbps);
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
    tableBody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted);">No links found matching criteria.</td></tr>`;
    return;
  }

  links.forEach(link => {
    const tr = document.createElement('tr');

    const legPct = link.leg_util_pct !== null && link.leg_util_pct !== undefined ? link.leg_util_pct : 0;
    const legColor = getBarColor(legPct);
    const legBar = createUtilBar(legPct, legColor);

    const mwPct = link.latest_metric && link.latest_metric.mw_util_pct !== null ? link.latest_metric.mw_util_pct : 0;
    const mwColor = getBarColor(mwPct);
    const mwBar = createUtilBar(mwPct, mwColor);

    const statusHtml = `<span class="status-badge ${link.status.toLowerCase()}">${link.status}</span>`;

    const latencyHtml = link.latency_ms !== null 
      ? `<span class="text-teal">${link.latency_ms}ms</span>` 
      : `<span class="text-muted">—</span>`;

    const capacityDisplay = formatCapacity(link.latest_metric && link.latest_metric.mw_capacity_mbps);

    // Prepare truncated display with tooltip containing full text
    const siteAFull = link.site_a || '';
    const siteBFull = link.site_b || '';
    const siteADisplay = siteAFull ? truncateText(siteAFull, 18) : '';
    const siteBDisplay = siteBFull ? truncateText(siteBFull, 18) : '';

    tr.innerHTML = `
      <td class="text-mono text-teal">${escapeHtml(link.link_id)}</td>
      <td>${escapeHtml(link.leg_name || '')}</td>
      <td class="col-site"><div class="truncate" title="${escapeHtml(siteAFull)}">${siteAFull ? escapeHtml(siteADisplay) : '<span class="text-muted">—</span>'}</div></td>
      <td class="col-site"><div class="truncate" title="${escapeHtml(siteBFull)}">${siteBFull ? escapeHtml(siteBDisplay) : '<span class="text-muted">—</span>'}</div></td>
      <td>${legBar}</td>
      <td>${mwBar}</td>
      <td>${capacityDisplay}</td>
      <td>${statusHtml}</td>
      <td class="text-mono">${latencyHtml}</td>
    `;

    const actionCell = document.createElement('td');
    actionCell.className = 'action-btns';
    actionCell.style.textAlign = 'right';

    const pingBtn = document.createElement('i');
    pingBtn.className = 'fa-solid fa-satellite-dish';
    pingBtn.title = 'Ping Link';
    pingBtn.style.cursor = 'pointer';
    pingBtn.addEventListener('click', () => window.manualPingLink(link.id, link.link_id, pingBtn));

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

    actionCell.appendChild(pingBtn);
    actionCell.appendChild(editBtn);
    actionCell.appendChild(deleteBtn);
    tr.appendChild(actionCell);

    tableBody.appendChild(tr);
  });
}

function createUtilBar(pct, colorVar) {
  const normalizedPct = Math.max(0, Math.min(100, Number(pct) || 0));
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - normalizedPct / 100);

  return `
    <div class="util-bar-container">
      <svg viewBox="0 0 42 42" aria-label="${Math.round(normalizedPct)}% utilization">
        <circle class="util-bar-bg" cx="21" cy="21" r="${radius}" />
        <circle class="util-bar-fill" cx="21" cy="21" r="${radius}" stroke-dasharray="${circumference.toFixed(2)}" stroke-dashoffset="${dashOffset.toFixed(2)}" style="stroke: var(${colorVar});" />
      </svg>
      <div class="util-bar-text">${Math.round(normalizedPct)}%</div>
    </div>
  `;
}

function formatCapacity(value) {
  if (value === null || value === undefined || value === '') {
    return '<span class="text-muted">—</span>';
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return '<span class="text-muted">—</span>';
  }
  return `${Math.round(num).toLocaleString()} Mbps`;
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

// Manual ping link function (triggered by per-row ping button)
window.manualPingLink = async (id, linkId, iconEl) => {
  // Disable icon and show spinner state
  const originalClass = iconEl.className;
  iconEl.className = 'fa-solid fa-spinner fa-spin';
  iconEl.style.pointerEvents = 'none';

  try {
    const result = await window.fetchAPI(`/api/links/${id}/ping`, { method: 'POST' });

    // Restore icon
    iconEl.className = originalClass;
    iconEl.style.pointerEvents = '';

    // Show result toast
    if (result.reachable) {
      const latency = result.latency_ms !== null ? ` — ${result.latency_ms.toFixed(1)}ms` : '';
      window.showToast(`${linkId}: reachable${latency}`, 'success');
    } else {
      window.showToast(`${linkId}: unreachable`, 'error');
    }

    // The row will auto-update via ws:link_status_update emitted by the backend
    // (ping_service already calls _emit_link_status_update after persist)

  } catch (err) {
    iconEl.className = originalClass;
    iconEl.style.pointerEvents = '';
    window.showToast(`Ping failed for ${linkId}: ${err.message}`, 'error');
  }
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  loadLegOptions();
  pollTable();

  // Listen for real-time link status updates via WebSocket
  window.addEventListener('ws:link_status_update', (event) => {
    handleLinkStatusUpdate(event.detail);
  });

  // Listen for ping cycle start to show a pinging indicator
  window.addEventListener('ws:ping_cycle_start', (event) => {
    // Add a subtle "pinging" indicator to the table header
    const tableHeader = document.querySelector('table thead tr');
    if (tableHeader && !document.getElementById('pinging-indicator')) {
      const indicator = document.createElement('div');
      indicator.id = 'pinging-indicator';
      indicator.style.cssText = 'color: var(--text-secondary); font-size: 0.85rem; padding: 4px 8px; margin-left: 8px; display: inline-block; animation: pulse 1.5s infinite;';
      indicator.textContent = '🔄 Pinging...';
      const headerCell = tableHeader.querySelector('th:last-child');
      if (headerCell) {
        headerCell.appendChild(indicator);
      }
    }
  });

  // Listen for ping cycle complete to remove the pinging indicator
  window.addEventListener('ws:ping_cycle_complete', (event) => {
    const indicator = document.getElementById('pinging-indicator');
    if (indicator) {
      indicator.remove();
    }
  });

  // Expose pollTable for modal.js to call after CRUD
  window.refreshTable = pollTable;
});
