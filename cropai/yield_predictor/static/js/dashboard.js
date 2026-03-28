// Dashboard Charts JavaScript
function initializeCharts(chartData) {
    if (!chartData || !chartData.labels || chartData.labels.length === 0) {
        console.log('No chart data available');
        return;
    }

    // Rainfall Chart
    const rainfallCtx = document.getElementById('rainfallChart');
    if (rainfallCtx) {
        new Chart(rainfallCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Rainfall (mm)',
                    data: chartData.rainfall,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true },
                    tooltip: { enabled: true }
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        title: { display: true, text: 'Rainfall (mm)' } 
                    }
                }
            }
        });
    }

    // Profit Chart
    const profitCtx = document.getElementById('profitChart');
    if (profitCtx) {
        new Chart(profitCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Net Profit (KES/ha)',
                    data: chartData.profit,
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: true },
                    tooltip: { enabled: true }
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        title: { display: true, text: 'Profit (KES/ha)' } 
                    }
                }
            }
        });
    }
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if chart data is available
    const chartDataElement = document.getElementById('chart-data');
    if (chartDataElement) {
        try {
            const chartData = JSON.parse(chartDataElement.textContent);
            initializeCharts(chartData);
        } catch (error) {
            console.error('Error parsing chart data:', error);
        }
    }
});