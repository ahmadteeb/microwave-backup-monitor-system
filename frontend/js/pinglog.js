const pingLogList = document.getElementById('ping-log-list');

async function pollPingLog() {
  try {
    const data = await window.fetchAPI('/api/ping-log?limit=50');
    renderPingLog(data.results);
  } catch (error) {
    console.error("Failed to fetch ping log", error);
  }
}

function renderPingLog(entries) {
  // To avoid constant reflows replacing all DOM, we will just rebuild for v1
  // since the list is short, but ideally we'd diff.
  
  // We want to render them in chronological order if possible, or newest at top.
  // The API returns newest first. The design shows newest at bottom if it auto-scrolls,
  // but typically newest at top is easier. Let's do newest at bottom like a terminal tail.
  
  const entriesToRender = [...entries].reverse(); // Newest last
  
  pingLogList.innerHTML = '';
  
  entriesToRender.forEach(entry => {
    const time = new Date(entry.timestamp).toLocaleTimeString('en-US', { hour12: false });
    
    let colorClass = 'ok';
    if (entry.status_text === 'TIMEOUT' || entry.status_text === 'ERR') {
      colorClass = 'err';
    } else if (entry.status_text === 'PKT_LOSS') {
      colorClass = 'warn';
    }
    
    const latency = entry.latency_ms !== null ? `${entry.latency_ms}ms` : 'ERR';
    
    const div = document.createElement('div');
    div.className = `log-entry ${colorClass}`;
    div.innerHTML = `
      <span>[${time}] ${entry.link_id} ${entry.status_text}</span>
      <span>${latency}</span>
    `;
    
    pingLogList.appendChild(div);
  });
  
  // Auto-scroll to bottom
  pingLogList.scrollTop = pingLogList.scrollHeight;
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    pollPingLog();
    setInterval(pollPingLog, 10000); // 10s interval per plan
  }, 100);
});
