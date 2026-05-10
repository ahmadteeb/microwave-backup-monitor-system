// DOM Elements
const kpiTotal = document.getElementById('kpi-total');
const kpiReachable = document.getElementById('kpi-reachable');
const kpiUnreachable = document.getElementById('kpi-unreachable');
const kpiHigh = document.getElementById('kpi-high');
const healthBadge = document.getElementById('sys-health-badge');
const nextCheckVal = document.getElementById('next-check-val');

// Global state for polling config
let PING_INTERVAL_SECONDS = 60; // fallback when backend config is unavailable
let lastPollAt = Date.now();

async function loadPollingConfig() {
  try {
    const settings = await fetchAPI('/api/settings/app');
    const interval = parseInt(settings.app?.ping_interval_seconds, 10);
    if (!Number.isNaN(interval) && interval > 0) {
      PING_INTERVAL_SECONDS = interval;
    }
  } catch (error) {
    console.warn('Unable to load polling configuration:', error);
  }
}

// KPI Update (called from WebSocket or initial fetch)
function handleKPIUpdate(data) {
  updateKPIValues(data);
  updateHealthBadge(data, null);
  lastPollAt = Date.now();
}

// Initial fetch (on page load, before WebSocket is ready)
async function fetchKPIs() {
  try {
    const data = await window.fetchAPI('/api/dashboard/kpi');
    handleKPIUpdate(data);
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
  const uptimeVal = document.getElementById('uptime-val');
  if (uptimeVal) {
    uptimeVal.textContent = data.link_availability_24h !== null && data.link_availability_24h !== undefined
      ? `${data.link_availability_24h}%`
      : (data.uptime_display || 'N/A');
  }
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
  const elapsed = Math.floor((Date.now() - lastPollAt) / 1000);
  const remaining = Math.max(0, PING_INTERVAL_SECONDS - elapsed);
  const m = Math.floor(remaining / 60).toString().padStart(2, '0');
  const s = (remaining % 60).toString().padStart(2, '0');
  if (nextCheckVal) nextCheckVal.textContent = `${m}:${s}`;
}

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
  await loadPollingConfig();
  await fetchKPIs();
  setInterval(tickCountdown, 1000);

  // Listen for real-time KPI updates via WebSocket
  window.addEventListener('ws:kpi_update', (event) => {
    handleKPIUpdate(event.detail);
  });

  // Listen for settings changes
  window.addEventListener('appSettingsUpdated', (event) => {
    const interval = event?.detail?.settings?.app?.ping_interval_seconds;
    if (interval) {
      const parsed = parseInt(interval, 10);
      if (!Number.isNaN(parsed) && parsed > 0) {
        PING_INTERVAL_SECONDS = parsed;
      }
    }
  });
});
