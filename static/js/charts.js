let stabilityChart = null;

async function pollStabilityChart() {
  try {
    const data = await window.fetchAPI('/api/dashboard/stability');
    updateChart(data.hours);
  } catch (error) {
    console.error("Failed to fetch stability data", error);
  }
}

function initChart() {
  const ctx = document.getElementById('stabilityChart').getContext('2d');
  
  Chart.defaults.color = '#8b949e';
  Chart.defaults.font.family = "'Inter', sans-serif";

  stabilityChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [], // Hours
      datasets: [
        {
          label: 'Successful',
          data: [],
          backgroundColor: '#00d4aa',
          stack: 'Stack 0',
        },
        {
          label: 'Failed',
          data: [],
          backgroundColor: '#ff6b6b',
          stack: 'Stack 0',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false // Hide legend to match design, or keep it minimal
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            footer: (tooltipItems) => {
              const success = tooltipItems[0].raw || 0;
              const failed = tooltipItems[1] ? (tooltipItems[1].raw || 0) : 0;
              const total = success + failed;
              const rate = total > 0 ? ((success / total) * 100).toFixed(1) : 0;
              return `Rate: ${rate}%`;
            }
          }
        }
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false, drawBorder: false },
          ticks: { maxTicksLimit: 12 }
        },
        y: {
          stacked: true,
          grid: { color: '#30363d', drawBorder: false },
          beginAtZero: true
        }
      }
    }
  });
}

function updateChart(hoursData) {
  if (!stabilityChart) return;
  
  const labels = hoursData.map(h => {
    const d = new Date(h.hour);
    return `${d.getHours()}:00`;
  });
  
  const successful = hoursData.map(h => h.successful);
  const failed = hoursData.map(h => h.failed);
  
  stabilityChart.data.labels = labels;
  stabilityChart.data.datasets[0].data = successful;
  stabilityChart.data.datasets[1].data = failed;
  
  stabilityChart.update();
}

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
      initChart();
      pollStabilityChart();
      setInterval(pollStabilityChart, 60000); // 60s interval
    } else {
      console.error("Chart.js failed to load");
    }
  }, 200);
});
