let trendsChart = null;
let typesChart = null;

document.addEventListener('DOMContentLoaded', function () {
    initializeSidebar();
    initializeCharts();
    addCardInteractivity();
    addLoadingAnimation();
    initializeEventListeners();

    const formatter = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    // Initialize charts with initial data
    if (typeof initialData !== 'undefined' && initialData) {
        console.log('Initial data:', initialData); // For debugging
        createTrendsChart(initialData.trends_data);
        createTypesChart(initialData.types_data);
    } else {
        console.error('Initial data is not defined.');
    }
});

function createTrendsChart(data) {
    const canvas = document.getElementById('activityTrendsChart');
    if (!canvas) {
        console.error('Canvas element for activity trends chart not found.');
        return;
    }
    const ctx = canvas.getContext('2d');
    
    if (trendsChart) {
        trendsChart.destroy();
    }

    trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Revenue',
                data: data.values,
                borderColor: '#4e73df',
                backgroundColor: 'rgba(78, 115, 223, 0.05)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: value => new Intl.NumberFormat('en-US', {
                            style: 'currency',
                            currency: 'USD'
                        }).format(value)
                    }
                }
            }
        }
    });
}

function createTypesChart(data) {
    const canvas = document.getElementById('activityTypesChart');
    if (!canvas) {
        console.error('Canvas element for activity types chart not found.');
        return;
    }
    const ctx = canvas.getContext('2d');

    if (typesChart) {
        typesChart.destroy();
    }

    typesChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: [
                    '#4e73df',
                    '#1cc88a',
                    '#36b9cc',
                    '#f6c23e',
                    '#e74a3b'
                ]
            }]
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });

        // Add keyboard support
        sidebarToggle.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                sidebar.classList.toggle('active');
            }
        });
    }
}

function initializeEventListeners() {
    // Refresh Data Button
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function () {
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin fa-sm"></i> Refreshing...';
            setTimeout(() => {
                initializeCharts();
                this.disabled = false;
                this.innerHTML = '<i class="fas fa-sync-alt fa-sm"></i> Refresh Data';
            }, 1000);
        });
    }

    // Time Period Buttons
    ['weeklyView', 'monthlyView', 'yearlyView'].forEach(id => {
        const button = document.getElementById(id);
        if (button) {
            button.addEventListener('click', function () {
                document.querySelectorAll('.btn-group .btn').forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                updateChartData(id);
            });
        }
    });
}

async function initializeCharts() {
    try {
        const response = await fetch('/api/activities-data/');
        const data = await response.json();
        createTrendsChart(data.trends_data);
        createTypesChart(data.types_data);
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

async function updateChartData(viewType) {
    try {
        const response = await fetch(`/api/activities-data/?view=${viewType}`);
        const data = await response.json();
        createTrendsChart(data.trends_data);
        createTypesChart(data.types_data);
    } catch (error) {
        console.error('Error updating chart data:', error);
    }
}

function addCardInteractivity() {
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.classList.add('shadow-lg');
        });
        card.addEventListener('mouseleave', () => {
            card.classList.remove('shadow-lg');
        });
    });
}

function addLoadingAnimation() {
    window.addEventListener('load', () => {
        const loadingElement = document.getElementById('loading');
        if (loadingElement) {
            loadingElement.style.display = 'none';
        }
    });
}

// Example usage of localization
const translations = {
    en: {
        sales: 'Sales',
        salesByAgent: 'Sales by Agent'
    },
    es: {
        sales: 'Ventas',
        salesByAgent: 'Ventas por Agente'
    }
};

function setLanguage(lang) {
    const salesElement = document.querySelector('[data-translate="sales"]');
    const salesByAgentElement = document.querySelector('[data-translate="salesByAgent"]');
    
    if (salesElement) salesElement.textContent = translations[lang].sales;
    if (salesByAgentElement) salesByAgentElement.textContent = translations[lang].salesByAgent;
}

async function updateDashboard(range = 'monthly') {
    try {
        const response = await fetch(`/api/activities-data/?range=${range}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Update KPI cards
        updateKPICards(data.kpi_data);
        
        // Update charts
        createTrendsChart(data.trends_data);
        createTypesChart(data.types_data);
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// Example usage
setLanguage('ar'); // Switch to Arabic