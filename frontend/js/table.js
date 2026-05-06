// DOM Elements
const tableBody = document.getElementById('link-table-body');
const searchInput = document.getElementById('search-input');
const statusFilter = document.getElementById('status-filter');
const legFilter = document.getElementById('leg-filter');
const btnPrevPage = document.getElementById('btn-prev-page');
const btnNextPage = document.getElementById('btn-next-page');
const pageInfo = document.getElementById('page-info');
const tableCount = document.getElementById('table-count');

// State
let currentPage = 1;
let totalPages = 1;
let searchTimeout = null;

// API Polling
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
    updateLegFilterOptions(data.links); // Simple dynamic extract for v1
  } catch (error) {
    console.error("Failed to fetch table data", error);
  }
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
    
    // Fiber Util Bar
    const fiberPct = link.latest_metric && link.latest_metric.fiber_util_pct !== null ? link.latest_metric.fiber_util_pct : 0;
    const fiberColor = getBarColor(fiberPct);
    const fiberBar = createUtilBar(fiberPct, fiberColor);
    
    // MW Util Bar
    const mwPct = link.latest_metric && link.latest_metric.mw_util_pct !== null ? link.latest_metric.mw_util_pct : 0;
    const mwColor = getBarColor(mwPct);
    const mwBar = createUtilBar(mwPct, mwColor);

    // Status Badge
    const statusHtml = `<span class="status-badge ${link.status.toLowerCase()}">${link.status}</span>`;
    
    // Latency
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
      <td class="action-btns" style="text-align: right;">
        <i class="fa-solid fa-pencil" onclick="window.openEditModal(${link.id})" title="Edit Link"></i>
        <i class="fa-solid fa-trash-can" onclick="window.deleteLink(${link.id}, '${link.link_id}')" title="Delete Link"></i>
      </td>
    `;
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

// Very basic distinct leg extraction from current page. 
// Ideally, backend provides a /api/legs endpoint.
const knownLegs = new Set();
function updateLegFilterOptions(links) {
  let changed = false;
  links.forEach(l => {
    if (!knownLegs.has(l.leg_name)) {
      knownLegs.add(l.leg_name);
      changed = true;
    }
  });
  
  if (changed) {
    const currentVal = legFilter.value;
    legFilter.innerHTML = '<option value="ALL_REGIONS">ALL_REGIONS</option>';
    Array.from(knownLegs).sort().forEach(leg => {
      legFilter.innerHTML += `<option value="${leg}">${leg}</option>`;
    });
    legFilter.value = currentVal;
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
  // Wait a tiny bit to ensure dashboard.js defines fetchAPI
  setTimeout(() => {
    pollTable();
    setInterval(pollTable, 30000);
    // Expose pollTable for modal.js to call after CRUD
    window.refreshTable = pollTable;
  }, 100);
});
