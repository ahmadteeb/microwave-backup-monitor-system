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
