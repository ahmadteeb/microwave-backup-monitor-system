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
const kpiTotal = document.getElementById('kpi-total');
const kpiReachable = document.getElementById('kpi-reachable');
const kpiUnreachable = document.getElementById('kpi-unreachable');
const kpiHigh = document.getElementById('kpi-high');
const healthBadge = document.getElementById('sys-health-badge');
const nextCheckVal = document.getElementById('next-check-val');

// Global state for polling config
const PING_INTERVAL_SECONDS = 60; // Should ideally come from backend config, hardcoded for v1 per plan
let nextCheckCountdown = PING_INTERVAL_SECONDS;

// KPI Polling
async function pollKPIs() {
  try {
    const data = await fetchAPI('/api/dashboard/kpi');
    updateKPIValues(data);
    updateHealthBadge(data, null);
  } catch (error) {
    updateHealthBadge(null, error);
  }
}

function updateKPIValues(data) {
  // Simple opacity animation for changes
  const animateValue = (el, val) => {
    if (el.textContent != val) {
      el.style.opacity = '0';
      setTimeout(() => {
        el.textContent = val;
        el.style.opacity = '1';
      }, 300);
    }
  };

  animateValue(kpiTotal, data.total_links);
  animateValue(kpiReachable, data.mw_reachable);
  animateValue(kpiUnreachable, data.mw_unreachable);
  animateValue(kpiHigh, data.high_utilization);
}

function updateHealthBadge(data, error) {
  healthBadge.classList.remove('degraded', 'down');
  
  if (error) {
    healthBadge.textContent = 'SYSTEM DOWN';
    healthBadge.classList.add('down');
    return;
  }

  // Derive degraded state: if we have unreachable links, or high utilization
  if (data.mw_unreachable > 0 || data.high_utilization > 0) {
    healthBadge.textContent = 'SYSTEM DEGRADED';
    healthBadge.classList.add('degraded');
  } else {
    healthBadge.textContent = 'SYSTEM HEALTHY';
  }
}

// Countdown Timer
function tickCountdown() {
  nextCheckCountdown--;
  if (nextCheckCountdown < 0) {
    nextCheckCountdown = PING_INTERVAL_SECONDS;
  }
  
  const m = Math.floor(nextCheckCountdown / 60).toString().padStart(2, '0');
  const s = (nextCheckCountdown % 60).toString().padStart(2, '0');
  nextCheckVal.textContent = `${m}:${s}`;
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  pollKPIs();
  setInterval(pollKPIs, 30000);
  setInterval(tickCountdown, 1000);
  
  // Make fetchAPI globally available for other scripts
  window.fetchAPI = fetchAPI;
});
