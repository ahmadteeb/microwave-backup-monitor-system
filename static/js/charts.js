let pingHistoryChart = null;
function renderPingHistoryChart(history) {
  const canvas = document.getElementById('ping-history-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  const dataPoints = (history || []).slice(0, 60).reverse();
  const labels = dataPoints.map(entry => {
    if (!entry.timestamp) return '';
    const d = new Date(entry.timestamp);
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  });

  const latencies = dataPoints.map(entry => entry.latency_ms || 0);
  const pointBackground = dataPoints.map(entry => {
    if (entry.packet_loss === 100) return '#ff6b6b';
    if (entry.packet_loss > 0) return '#ffb366';
    return '#00d4aa';
  });

  const config = {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Latency (ms)',
        data: latencies,
        borderColor: '#00d4aa',
        backgroundColor: 'rgba(0, 212, 170, 0.2)',
        pointBackgroundColor: pointBackground,
        fill: true,
        tension: 0.25,
        pointRadius: 3,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxTicksLimit: 10 }
        },
        y: {
          grid: { color: '#30363d' },
          beginAtZero: true,
          title: { display: true, text: 'ms' }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.parsed.y} ms`
          }
        }
      }
    }
  };

  if (!pingHistoryChart) {
    pingHistoryChart = new Chart(canvas.getContext('2d'), config);
  } else {
    pingHistoryChart.data = config.data;
    pingHistoryChart.options = config.options;
    pingHistoryChart.update();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (typeof Chart !== 'undefined') {
      // Chart.js loaded successfully, ping history chart will be initialized when modal opens
    } else {
      console.error("Chart.js failed to load");
    }
  }, 200);
});
