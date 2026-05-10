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
let PING_INTERVAL_SECONDS = 60; // fallback when backend config is unavailable
let nextCheckCountdown = PING_INTERVAL_SECONDS;
let pollIntervalId = null;

async function loadPollingConfig() {
  try {
    const settings = await fetchAPI('/api/settings/app');
    const interval = parseInt(settings.app?.ping_interval_seconds, 10);
    if (!Number.isNaN(interval) && interval > 0) {
      PING_INTERVAL_SECONDS = interval;
      nextCheckCountdown = PING_INTERVAL_SECONDS;
    }
  } catch (error) {
    console.warn('Unable to load polling configuration:', error);
  }
}

function schedulePolling() {
  if (pollIntervalId) {
    clearInterval(pollIntervalId);
  }
  pollIntervalId = setInterval(pollKPIs, PING_INTERVAL_SECONDS * 1000);
}

function applyPollingConfig(intervalSeconds) {
  if (!Number.isNaN(intervalSeconds) && intervalSeconds > 0) {
    PING_INTERVAL_SECONDS = intervalSeconds;
    nextCheckCountdown = PING_INTERVAL_SECONDS;
    schedulePolling();
  }
}

// KPI Polling
async function pollKPIs() {
  try {
    const data = await fetchAPI('/api/dashboard/kpi');
    updateKPIValues(data);
    updateHealthBadge(data, null);
  } catch (error) {
    updateHealthBadge(null, error);
  } finally {
    nextCheckCountdown = PING_INTERVAL_SECONDS;
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
  if (data.uptime_display) {
    const uptimeVal = document.getElementById('uptime-val');
    if (uptimeVal) {
      uptimeVal.textContent = data.uptime_display;
    }
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
  nextCheckCountdown--;
  if (nextCheckCountdown < 0) {
    nextCheckCountdown = PING_INTERVAL_SECONDS;
  }
  
  const m = Math.floor(nextCheckCountdown / 60).toString().padStart(2, '0');
  const s = (nextCheckCountdown % 60).toString().padStart(2, '0');
  nextCheckVal.textContent = `${m}:${s}`;
}

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
  await loadPollingConfig();
  pollKPIs();
  schedulePolling();
  setInterval(tickCountdown, 1000);
  
  // Make fetchAPI globally available for other scripts
  window.fetchAPI = fetchAPI;

  window.addEventListener('appSettingsUpdated', (event) => {
    const interval = event?.detail?.settings?.app?.ping_interval_seconds;
    if (interval) {
      applyPollingConfig(interval);
    }
  });
});
