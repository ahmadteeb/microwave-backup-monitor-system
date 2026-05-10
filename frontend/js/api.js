window.fetchAPI = async function(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error || `HTTP error ${response.status}`);
  }
  return response.json();
};

// WebSocket connection via Socket.IO
(function initSocket() {
  function connect() {
    if (typeof io === 'undefined') {
      // Socket.IO library not loaded yet, retry
      setTimeout(connect, 200);
      return;
    }

    const socket = io({
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity
    });

    socket.on('connect', () => {
      console.log('[WS] Connected:', socket.id);
      window.dispatchEvent(new CustomEvent('ws:connected'));
    });

    socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason);
      window.dispatchEvent(new CustomEvent('ws:disconnected'));
    });

    // Relay server events as DOM CustomEvents so each module can listen independently
    socket.on('kpi_update', (data) => {
      window.dispatchEvent(new CustomEvent('ws:kpi_update', { detail: data }));
    });

    socket.on('link_status_update', (data) => {
      window.dispatchEvent(new CustomEvent('ws:link_status_update', { detail: data }));
    });

    socket.on('notification_new', (data) => {
      window.dispatchEvent(new CustomEvent('ws:notification_new', { detail: data }));
    });

    window._socket = socket;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connect);
  } else {
    connect();
  }
})();
