// Chart.js configurations and management
class ChartManager {
    constructor() {
        this.metricsChart = null;
        this.healthChart = null;
        this.metricsHistory = {
            labels: [],
            latency: [],
            utilization: [],
            alerts: []
        };
        this.maxDataPoints = 50; // Keep last 50 data points
    }

    initializeCharts() {
        this.initializeMetricsChart();
        this.initializeHealthChart();
    }

    initializeMetricsChart() {
        const ctx = document.getElementById('metricsChart');
        if (!ctx) return;

        this.metricsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Average Latency (μs)',
                        data: [],
                        borderColor: '#64ffda',
                        backgroundColor: 'rgba(100, 255, 218, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Average Utilization (%)',
                        data: [],
                        borderColor: '#ff6b6b',
                        backgroundColor: 'rgba(255, 107, 107, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Active Alerts',
                        data: [],
                        borderColor: '#feca57',
                        backgroundColor: 'rgba(254, 202, 87, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y2'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#e0e0e0',
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255,255,255,0.2)',
                        borderWidth: 1
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time',
                            color: '#b0b0b0'
                        },
                        ticks: {
                            color: '#b0b0b0',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Latency (μs)',
                            color: '#64ffda'
                        },
                        ticks: {
                            color: '#64ffda',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            color: 'rgba(100, 255, 218, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Utilization (%)',
                            color: '#ff6b6b'
                        },
                        ticks: {
                            color: '#ff6b6b',
                            font: {
                                size: 10
                            }
                        },
                        grid: {
                            drawOnChartArea: false,
                        }
                    },
                    y2: {
                        type: 'linear',
                        display: false,
                        position: 'right',
                        title: {
                            display: false
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 2,
                        hoverRadius: 4
                    }
                },
                animation: {
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    initializeHealthChart() {
        const ctx = document.getElementById('healthChart');
        if (!ctx) return;

        this.healthChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Excellent', 'Good', 'Fair', 'Poor', 'Critical'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#27ae60',  // Excellent - Green
                        '#2ecc71',  // Good - Light Green
                        '#f39c12',  // Fair - Orange
                        '#e67e22',  // Poor - Dark Orange
                        '#e74c3c'   // Critical - Red
                    ],
                    borderColor: [
                        '#27ae60',
                        '#2ecc71',
                        '#f39c12',
                        '#e67e22',
                        '#e74c3c'
                    ],
                    borderWidth: 2,
                    hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#e0e0e0',
                            font: {
                                size: 10
                            },
                            padding: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: 'rgba(255,255,255,0.2)',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.parsed / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%',
                animation: {
                    animateRotate: true,
                    animateScale: true,
                    duration: 1000
                }
            }
        });
    }

    updateMetricsChart(kpiData) {
        if (!this.metricsChart) return;

        const now = new Date();
        const timeLabel = now.toLocaleTimeString();

        // Add new data point
        this.metricsHistory.labels.push(timeLabel);
        this.metricsHistory.latency.push(kpiData.avg_latency || 0);
        this.metricsHistory.utilization.push((kpiData.avg_utilization * 100) || 0);
        this.metricsHistory.alerts.push(kpiData.active_alerts || 0);

        // Keep only recent data points
        if (this.metricsHistory.labels.length > this.maxDataPoints) {
            this.metricsHistory.labels.shift();
            this.metricsHistory.latency.shift();
            this.metricsHistory.utilization.shift();
            this.metricsHistory.alerts.shift();
        }

        // Update chart data
        this.metricsChart.data.labels = this.metricsHistory.labels;
        this.metricsChart.data.datasets[0].data = this.metricsHistory.latency;
        this.metricsChart.data.datasets[1].data = this.metricsHistory.utilization;
        this.metricsChart.data.datasets[2].data = this.metricsHistory.alerts;

        this.metricsChart.update('none'); // Update without animation for real-time feel
    }

    updateHealthChart(healthData) {
        if (!this.healthChart) {
            console.log('Health chart not initialized');
            return;
        }

        console.log('Updating health chart with data:', healthData);

        // Initialize distribution counters
        const distribution = {
            excellent: 0,  // >= 0.9
            good: 0,       // >= 0.7
            fair: 0,       // >= 0.5
            poor: 0,       // >= 0.3
            critical: 0    // < 0.3
        };

        // Handle empty or invalid data
        if (!healthData || typeof healthData !== 'object' || Object.keys(healthData).length === 0) {
            console.log('No health data available for chart');
            this.healthChart.data.datasets[0].data = [0, 0, 0, 0, 0];
            this.healthChart.update();
            return;
        }

        // Process health data and categorize
        let totalLinks = 0;
        Object.entries(healthData).forEach(([linkId, healthInfo]) => {
            totalLinks++;
            
            // Extract score - handle both formats: direct number or object with score
            let score;
            if (typeof healthInfo === 'number') {
                score = healthInfo;
            } else if (typeof healthInfo === 'object' && healthInfo !== null) {
                score = healthInfo.score || healthInfo.health_indicator || 0;
            } else {
                score = 0;
            }

            // Categorize based on score
            if (score >= 0.9) {
                distribution.excellent++;
            } else if (score >= 0.7) {
                distribution.good++;
            } else if (score >= 0.5) {
                distribution.fair++;
            } else if (score >= 0.3) {
                distribution.poor++;
            } else {
                distribution.critical++;
            }
        });

        console.log('Health distribution calculated:', distribution);
        console.log('Total links processed:', totalLinks);

        // Update chart data
        this.healthChart.data.datasets[0].data = [
            distribution.excellent,
            distribution.good,
            distribution.fair,
            distribution.poor,
            distribution.critical
        ];

        // Trigger chart update
        this.healthChart.update();
    }

    createLatencyHistogram(telemetryData) {
        // Create a histogram of latency values
        const latencies = Object.values(telemetryData).map(t => t.latency || 0);
        
        if (latencies.length === 0) return null;

        const bins = 10;
        const min = Math.min(...latencies);
        const max = Math.max(...latencies);
        const binSize = (max - min) / bins;
        
        const histogram = new Array(bins).fill(0);
        const labels = [];
        
        for (let i = 0; i < bins; i++) {
            const binStart = min + (i * binSize);
            const binEnd = binStart + binSize;
            labels.push(`${binStart.toFixed(1)}-${binEnd.toFixed(1)}μs`);
            
            histogram[i] = latencies.filter(lat => 
                lat >= binStart && (i === bins - 1 ? lat <= binEnd : lat < binEnd)
            ).length;
        }

        return {
            labels: labels,
            data: histogram
        };
    }

    createUtilizationHeatmap(telemetryData) {
        // Create utilization heatmap data
        const utilData = [];
        Object.entries(telemetryData).forEach(([linkId, data]) => {
            utilData.push({
                link: linkId,
                utilization: data.utilization || 0,
                health: data.health_indicator || 1.0
            });
        });

        return utilData.sort((a, b) => b.utilization - a.utilization);
    }

    exportChartData() {
        // Export current chart data for analysis
        return {
            metrics_history: this.metricsHistory,
            timestamp: new Date().toISOString()
        };
    }

    resetCharts() {
        // Reset all chart data
        this.metricsHistory = {
            labels: [],
            latency: [],
            utilization: [],
            alerts: []
        };

        if (this.metricsChart) {
            this.metricsChart.data.labels = [];
            this.metricsChart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            this.metricsChart.update();
        }

        if (this.healthChart) {
            this.healthChart.data.datasets[0].data = [0, 0, 0, 0, 0];
            this.healthChart.update();
        }
    }
}

// Global chart manager instance
let chartManager = null;

// Initialize charts
function initializeCharts() {
    chartManager = new ChartManager();
    chartManager.initializeCharts();
}

// Update charts with new data
function updateCharts() {
    if (!chartManager) return;

    // Update metrics chart with KPI data
    fetch('/api/kpis')
        .then(response => response.json())
        .then(kpiData => {
            chartManager.updateMetricsChart(kpiData);
        })
        .catch(error => console.error('Error updating metrics chart:', error));

    // Update health chart with health data
    // Update health chart with health data
fetch('/api/telemetry/health')
    .then(response => response.json())
    .then(healthData => {
        console.log('Received health data for chart:', healthData);

        // Pass only the scores object, not the whole response
        const scores = healthData.health_scores || {};
        chartManager.updateHealthChart(scores);
    })
    .catch(error => {
        console.error('Error updating health chart:', error);
        if (chartManager && chartManager.healthChart) {
            chartManager.healthChart.data.datasets[0].data = [0, 0, 0, 0, 0];
            chartManager.healthChart.update();
        }
    });

    }

// Create additional visualization charts
function createAdditionalCharts(containerId, telemetryData) {
    if (!chartManager || !telemetryData) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    // Create latency histogram
    const latencyHist = chartManager.createLatencyHistogram(telemetryData);
    if (latencyHist) {
        // Add histogram chart to container
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);

        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: latencyHist.labels,
                datasets: [{
                    label: 'Link Count',
                    data: latencyHist.data,
                    backgroundColor: 'rgba(100, 255, 218, 0.6)',
                    borderColor: '#64ffda',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Latency Distribution',
                        color: '#e0e0e0'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#b0b0b0'
                        },
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#b0b0b0',
                            maxRotation: 45
                        },
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        }
                    }
                }
            }
        });
    }
}