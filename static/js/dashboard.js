// Cat-Emails Dashboard JavaScript
// Handles all dashboard interactions, data fetching, and chart rendering

// Global variables
let currentPeriod = 'week';
let charts = {};
let currentCategoriesView = 'combined';

// Store categories data globally for view switching
window.categoriesData = [];

// Dashboard initialization
function initializeDashboard() {
    console.log('Initializing Cat-Emails Dashboard...');
    
    // Initialize Chart.js defaults
    Chart.defaults.responsive = true;
    Chart.defaults.maintainAspectRatio = false;
    Chart.defaults.plugins.legend.position = 'bottom';
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    console.log('Dashboard initialized successfully');
}

// Data fetching functions
async function fetchData(endpoint) {
    try {
        showLoading();
        const response = await fetch(endpoint);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error occurred');
        }
        
        return data.data;
    } catch (error) {
        console.error(`Error fetching data from ${endpoint}:`, error);
        showError(`Failed to load data: ${error.message}`);
        throw error;
    } finally {
        hideLoading();
    }
}

async function refreshDashboardData(period = 'week') {
    currentPeriod = period;
    console.log(`Refreshing dashboard data for period: ${period}`);
    
    try {
        showLoading();
        
        // Update timestamps
        const now = new Date();
        const timeString = now.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const lastUpdatedEl = document.getElementById('dashboard-last-updated');
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = `Last updated: ${timeString}`;
        }
        
        const navLastUpdated = document.getElementById('last-updated');
        if (navLastUpdated) {
            navLastUpdated.textContent = `Updated ${timeString}`;
        }
        
        // Fetch all data in parallel for better performance
        const [overviewResult, categoriesResult] = await Promise.allSettled([
            refreshOverviewStats(period),
            refreshCategoriesData()
        ]);
        
        // Handle any errors gracefully
        if (overviewResult.status === 'rejected') {
            console.error('Failed to load overview stats:', overviewResult.reason);
            showError('Failed to load overview statistics');
        }
        
        if (categoriesResult.status === 'rejected') {
            console.error('Failed to load categories:', categoriesResult.reason);
            showError('Failed to load categories data');
        }
        
        // Refresh active analytics tab if any
        const activeTab = document.querySelector('#analytics-tabs .nav-link.active');
        if (activeTab) {
            const targetId = activeTab.getAttribute('data-bs-target');
            await handleAnalyticsTabSwitch(targetId);
        }
        
        console.log('Dashboard data refreshed successfully');
        // Only show success toast for manual refreshes, not initial page load
        if (window.dashboardInitialized) {
            showSuccess('Dashboard updated successfully');
        } else {
            window.dashboardInitialized = true;
        }
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('Failed to refresh dashboard data');
    } finally {
        hideLoading();
    }
}

async function refreshOverviewStats(period) {
    try {
        const data = await fetchData(`/api/stats/overview?period=${period}`);
        const metrics = data.metrics;
        
        // Update main metrics with enhanced display
        const totalProcessed = metrics.total_processed || 0;
        const totalDeleted = (metrics.total_deleted || 0) + (metrics.total_archived || 0);
        const avgProcessingTime = metrics.avg_processing_seconds || 0;
        
        // Update metric values with animation classes
        updateMetricWithAnimation('total-processed', formatNumber(totalProcessed));
        updateMetricWithAnimation('total-deleted', formatNumber(totalDeleted));
        updateMetricWithAnimation('avg-processing', formatDuration(avgProcessingTime));
        
        // Calculate and display deletion rate
        const deletionRate = totalProcessed > 0 
            ? ((totalDeleted / totalProcessed) * 100).toFixed(1) 
            : '0';
        document.getElementById('deletion-rate').textContent = `${deletionRate}%`;
        
        // Update subtitles with contextual information
        document.getElementById('processed-subtitle').textContent = `${period} period`;
        document.getElementById('categories-subtitle').textContent = 'unique categories found';
        
        // Get and display categories count
        const categoriesData = await fetchData(`/api/stats/categories?period=${period}&limit=25`);
        const activeCategories = categoriesData.length;
        updateMetricWithAnimation('active-categories', activeCategories);
        
        // Update categories count badge
        const categoriesBadge = document.getElementById('categories-count-badge');
        if (categoriesBadge) {
            categoriesBadge.textContent = `Top ${Math.min(activeCategories, 25)}`;
        }
        
        // Update efficiency rating and trend indicators
        const efficiency = calculateEfficiency(metrics);
        const efficiencyEl = document.getElementById('processing-efficiency');
        if (efficiencyEl) {
            efficiencyEl.textContent = efficiency;
            efficiencyEl.className = `badge ${getEfficiencyBadgeClass(efficiency)} small`;
        }
        
        // Update trend indicators (mock data for now - would be calculated from historical data)
        updateTrendIndicator('processed-trend', getTrendDirection(totalProcessed));
        
    } catch (error) {
        console.error('Error refreshing overview stats:', error);
        // Set error states for metrics
        ['total-processed', 'total-deleted', 'avg-processing', 'active-categories'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.textContent = '--';
        });
    }
}

// Keep the old function name for compatibility - redirects to new function
async function handleTabSwitch(targetId) {
    return handleAnalyticsTabSwitch(targetId);
}

// Enhanced Categories data refresh with multiple views support
async function refreshCategoriesData() {
    try {
        // Show loading state
        showCategoriesLoading();
        
        const data = await fetchData(`/api/stats/categories?period=${currentPeriod}&limit=25`);
        
        // Store data globally for view switching
        window.categoriesData = data;
        
        // Calculate total for percentages
        const total = data.reduce((sum, cat) => sum + cat.count, 0);
        
        // Add percentage calculations to data
        data.forEach(category => {
            category.percentage = total > 0 ? parseFloat((category.count / total * 100).toFixed(1)) : 0;
        });
        
        if (data.length === 0) {
            showEmptyCategories();
            return;
        }
        
        // Update all views based on current selection
        updateCategoriesList(data);
        renderCategoriesChart(data);
        renderCategoriesColumns(data);
        
        // Hide loading states
        hideCategoriesLoading();
        
        console.log(`Loaded ${data.length} categories for ${currentPeriod} period`);
        
    } catch (error) {
        console.error('Error refreshing categories data:', error);
        showCategoriesError();
    }
}

// Helper functions for loading states
function showCategoriesLoading() {
    const loadingHtml = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading categories...</span>
            </div>
            <p class="mt-3 text-muted">Loading top 25 categories...</p>
        </div>
    `;
    
    const listContainer = document.getElementById('categories-list');
    if (listContainer) listContainer.innerHTML = loadingHtml;
    
    const chartLoading = document.getElementById('chart-loading');
    if (chartLoading) chartLoading.classList.remove('d-none');
}

function hideCategoriesLoading() {
    const chartLoading = document.getElementById('chart-loading');
    if (chartLoading) chartLoading.classList.add('d-none');
}

function showEmptyCategories() {
    const emptyHtml = `
        <div class="empty-state">
            <i class="bi bi-inbox"></i>
            <h6 class="text-muted mt-2">No Categories Found</h6>
            <p class="text-muted small mb-0">No email categories available for the selected period.</p>
        </div>
    `;
    
    const listContainer = document.getElementById('categories-list');
    if (listContainer) listContainer.innerHTML = emptyHtml;
}

function showCategoriesError() {
    const errorHtml = `
        <div class="error-state">
            <i class="bi bi-exclamation-triangle"></i>
            <h6 class="text-muted mt-2">Failed to Load</h6>
            <p class="text-muted small mb-2">Unable to load categories data.</p>
            <button class="btn btn-sm btn-outline-primary" onclick="refreshCategoriesData()">
                <i class="bi bi-arrow-clockwise me-1"></i>Retry
            </button>
        </div>
    `;
    
    const listContainer = document.getElementById('categories-list');
    if (listContainer) listContainer.innerHTML = errorHtml;
}

// Enhanced category list item creation
function createCategoryListItem(category, index) {
    const item = document.createElement('div');
    item.className = 'list-group-item category-list-item';
    
    // Enhanced badge colors based on ranking
    const badgeColor = index <= 3 ? 'bg-warning' : 
                      index <= 8 ? 'bg-primary' : 
                      index <= 15 ? 'bg-info' : 'bg-secondary';
    
    // Determine trend icon (mock for now - would be calculated from historical data)
    const trendIcon = getTrendIcon(category.trend || 'stable');
    const trendColor = getTrendColor(category.trend || 'stable');
    
    item.innerHTML = `
        <div class="category-item w-100">
            <div class="d-flex align-items-center">
                <span class="badge ${badgeColor} badge-count me-3 position-relative">
                    ${index}
                    ${index <= 3 ? '<i class="bi bi-star-fill position-absolute top-0 start-100 translate-middle text-warning" style="font-size: 0.5rem;"></i>' : ''}
                </span>
                <div class="category-details flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <div class="category-name fw-semibold text-dark" title="${category.display_name || category.name}">
                            ${category.name}
                        </div>
                        <span class="ms-2 ${trendColor}" title="Trend: ${category.trend || 'stable'}">
                            ${trendIcon}
                        </span>
                    </div>
                    <div class="category-stats small text-muted">
                        <span class="fw-medium">${formatNumber(category.count)}</span> emails
                        ${category.deleted > 0 ? `<span class="text-warning ms-2">• ${formatNumber(category.deleted)} filtered</span>` : ''}
                    </div>
                </div>
            </div>
            <div class="text-end ms-3">
                <div class="percentage-display">
                    <span class="badge bg-light text-primary fw-semibold">${category.percentage}%</span>
                </div>
                <div class="progress mt-2" style="height: 4px; width: 60px;">
                    <div class="progress-bar" role="progressbar" style="width: ${category.percentage}%" 
                         aria-valuenow="${category.percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        </div>
    `;
    
    // Add hover effects and animations
    item.addEventListener('mouseenter', () => {
        item.classList.add('slide-in-right');
    });
    
    item.addEventListener('mouseleave', () => {
        item.classList.remove('slide-in-right');
    });
    
    return item;
}

// Update categories list with enhanced rendering
function updateCategoriesList(data) {
    const listContainer = document.getElementById('categories-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    data.forEach((category, index) => {
        const listItem = createCategoryListItem(category, index + 1);
        listContainer.appendChild(listItem);
        
        // Stagger animations for better visual effect
        setTimeout(() => {
            listItem.classList.add('fade-in');
        }, index * 50);
    });
}

// Render categories in column layout for list view
function renderCategoriesColumns(data) {
    const columns = ['categories-col-1', 'categories-col-2', 'categories-col-3'];
    const itemsPerColumn = Math.ceil(data.length / 3);
    
    columns.forEach((colId, colIndex) => {
        const column = document.getElementById(colId);
        if (!column) return;
        
        column.innerHTML = '';
        
        const startIndex = colIndex * itemsPerColumn;
        const endIndex = Math.min(startIndex + itemsPerColumn, data.length);
        
        for (let i = startIndex; i < endIndex; i++) {
            const category = data[i];
            const listItem = createCategoryListItem(category, i + 1);
            listItem.classList.remove('list-group-item');
            listItem.classList.add('card', 'border-0', 'shadow-sm', 'mb-3');
            listItem.innerHTML = `<div class="card-body p-3">${listItem.innerHTML}</div>`;
            column.appendChild(listItem);
        }
    });
}

// Enhanced chart rendering with multiple chart types
function renderCategoriesChart(data, chartElementId = 'categories-chart') {
    const ctx = document.getElementById(chartElementId);
    if (!ctx) return;
    
    // Destroy existing chart
    const chartKey = chartElementId.replace('-', '_');
    if (charts[chartKey]) {
        charts[chartKey].destroy();
    }
    
    if (data.length === 0) {
        ctx.style.display = 'none';
        return;
    }
    
    ctx.style.display = 'block';
    
    // Prepare data for visualization (top 12 for better readability)
    const topCategories = data.slice(0, 12);
    const labels = topCategories.map(cat => truncateText(cat.name, 20));
    const values = topCategories.map(cat => cat.count);
    const colors = generateEnhancedColors(topCategories.length);
    
    // Determine chart type based on element and data
    const chartType = chartElementId.includes('full') ? 'bar' : 'doughnut';
    
    const chartConfig = {
        type: chartType,
        data: {
            labels: labels,
            datasets: [{
                label: 'Email Count',
                data: values,
                backgroundColor: colors.backgrounds,
                borderColor: colors.borders,
                borderWidth: 2,
                hoverBackgroundColor: colors.hovers,
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 800,
                easing: 'easeInOutCubic'
            },
            plugins: {
                legend: {
                    position: chartType === 'bar' ? 'top' : 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 11,
                            weight: '500'
                        },
                        generateLabels: function(chart) {
                            const original = Chart.defaults.plugins.legend.labels.generateLabels;
                            const labels = original.call(this, chart);
                            
                            // Add count to legend labels
                            labels.forEach((label, index) => {
                                if (index < values.length) {
                                    label.text = `${label.text} (${formatNumber(values[index])})`;
                                }
                            });
                            
                            return labels;
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(13, 110, 253, 0.95)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed.y || context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? (value / total * 100).toFixed(1) : '0';
                            return [
                                `Emails: ${formatNumber(value)}`,
                                `Percentage: ${percentage}%`
                            ];
                        }
                    }
                }
            },
            // Bar chart specific options
            ...(chartType === 'bar' && {
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatNumber(value);
                            }
                        }
                    }
                }
            }),
            // Doughnut chart specific options
            ...(chartType === 'doughnut' && {
                cutout: '60%',
                elements: {
                    arc: {
                        borderWidth: 2,
                        hoverBorderWidth: 4
                    }
                }
            })
        }
    };
    
    charts[chartKey] = new Chart(ctx, chartConfig);
    
    // Add click interactions for bar chart
    if (chartType === 'bar') {
        charts[chartKey].options.onClick = function(event, activeElements) {
            if (activeElements.length > 0) {
                const categoryIndex = activeElements[0].index;
                const category = topCategories[categoryIndex];
                showCategoryDetails(category);
            }
        };
    }
}

// Senders tab functions
async function refreshSendersData() {
    try {
        const data = await fetchData(`/api/stats/senders?period=${currentPeriod}&limit=25`);
        
        // Update list
        const listContainer = document.getElementById('senders-list');
        listContainer.innerHTML = '';
        
        if (data.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-person-x"></i>
                    <p>No senders found for this period</p>
                </div>
            `;
        } else {
            data.forEach((sender, index) => {
                const listItem = createSenderListItem(sender, index + 1);
                listContainer.appendChild(listItem);
            });
        }
        
        // Update chart
        renderSendersChart(data.slice(0, 10)); // Top 10 for chart
        
    } catch (error) {
        console.error('Error refreshing senders data:', error);
        document.getElementById('senders-list').innerHTML = `
            <div class="error-state">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Error loading senders</p>
            </div>
        `;
    }
}

// Accounts functions
async function fetchAccountsData() {
    try {
        const response = await fetch('/api/accounts');
        const data = await response.json();
        
        return data.accounts;
    } catch (error) {
        console.error('Error fetching accounts data:', error);
        throw error;
    }
}

async function deleteAccount(emailAddress) {
    try {
        const response = await fetch(`/api/accounts/${emailAddress}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error deleting account:', error);
        throw error;
    }
}

function createSenderListItem(sender, index) {
    const item = document.createElement('div');
    item.className = 'list-group-item sender-item';
    
    const displayName = sender.name || sender.email.split('@')[0];
    
    item.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="sender-details flex-grow-1">
                <div class="d-flex align-items-center mb-1">
                    <span class="badge bg-primary badge-count me-2">${index}</span>
                    <span class="sender-name fw-medium">${truncateText(displayName, 30)}</span>
                </div>
                <div class="sender-email text-muted small">${sender.email}</div>
                <small class="text-muted">
                    ${formatNumber(sender.count)} emails
                    ${sender.deleted > 0 ? `• ${formatNumber(sender.deleted)} deleted` : ''}
                </small>
            </div>
            <div class="text-end">
                <span class="badge bg-light text-dark">${formatNumber(sender.count)}</span>
            </div>
        </div>
    `;
    
    return item;
}

function renderSendersChart(data) {
    const ctx = document.getElementById('senders-chart');
    
    // Destroy existing chart
    if (charts.senders) {
        charts.senders.destroy();
    }
    
    const labels = data.map(sender => {
        const displayName = sender.name || sender.email.split('@')[0];
        return truncateText(displayName, 20);
    });
    const values = data.map(sender => sender.count);
    
    charts.senders = new Chart(ctx, {
        type: 'horizontalBar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Email Count',
                data: values,
                backgroundColor: 'rgba(13, 110, 253, 0.8)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

// Domains tab functions
async function refreshDomainsData() {
    try {
        const data = await fetchData(`/api/stats/domains?period=${currentPeriod}&limit=25`);
        
        // Update list
        const listContainer = document.getElementById('domains-list');
        listContainer.innerHTML = '';
        
        if (data.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-globe"></i>
                    <p>No domains found for this period</p>
                </div>
            `;
        } else {
            data.forEach((domain, index) => {
                const listItem = createDomainListItem(domain, index + 1);
                listContainer.appendChild(listItem);
            });
        }
        
        // Update chart
        renderDomainsChart(data.slice(0, 10)); // Top 10 for chart
        
    } catch (error) {
        console.error('Error refreshing domains data:', error);
        document.getElementById('domains-list').innerHTML = `
            <div class="error-state">
                <i class="bi bi-exclamation-triangle"></i>
                <p>Error loading domains</p>
            </div>
        `;
    }
}

function createDomainListItem(domain, index) {
    const item = document.createElement('div');
    const statusClass = domain.is_blocked ? 'domain-blocked' : 'domain-allowed';
    item.className = `list-group-item ${statusClass}`;
    
    const statusIcon = domain.is_blocked ? 
        '<i class="bi bi-shield-x text-danger"></i>' : 
        '<i class="bi bi-shield-check text-success"></i>';
    
    const statusText = domain.is_blocked ? 'Blocked' : 'Allowed';
    const statusBadge = domain.is_blocked ? 
        'bg-danger-subtle text-danger' : 
        'bg-success-subtle text-success';
    
    item.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="domain-details flex-grow-1">
                <div class="d-flex align-items-center mb-1">
                    <span class="badge bg-primary badge-count me-2">${index}</span>
                    <span class="fw-medium">${domain.domain}</span>
                    <span class="ms-2">${statusIcon}</span>
                </div>
                <small class="text-muted">
                    ${formatNumber(domain.count)} emails
                    ${domain.deleted > 0 ? `• ${formatNumber(domain.deleted)} deleted` : ''}
                </small>
            </div>
            <div class="text-end">
                <div class="badge ${statusBadge} mb-1">${statusText}</div>
                <div class="badge bg-light text-dark">${formatNumber(domain.count)}</div>
            </div>
        </div>
    `;
    
    return item;
}

function renderDomainsChart(data) {
    const ctx = document.getElementById('domains-chart');
    
    // Destroy existing chart
    if (charts.domains) {
        charts.domains.destroy();
    }
    
    const labels = data.map(domain => truncateText(domain.domain, 25));
    const values = data.map(domain => domain.count);
    const colors = data.map(domain => 
        domain.is_blocked ? 'rgba(220, 53, 69, 0.8)' : 'rgba(25, 135, 84, 0.8)'
    );
    
    charts.domains = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Email Count',
                data: values,
                backgroundColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

// Trends tab functions
async function refreshTrendsData(days = 30) {
    try {
        const data = await fetchData(`/api/stats/trends?days=${days}`);
        renderTrendsChart(data);
    } catch (error) {
        console.error('Error refreshing trends data:', error);
    }
}

function renderTrendsChart(trendsData) {
    const ctx = document.getElementById('trends-chart');
    
    // Destroy existing chart
    if (charts.trends) {
        charts.trends.destroy();
    }
    
    // Process trends data
    const datasets = [];
    const colors = ['#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0', '#6f42c1', '#fd7e14'];
    let colorIndex = 0;
    
    // Get top categories by total volume
    const categoriesByVolume = Object.entries(trendsData)
        .map(([category, points]) => ({
            category,
            points,
            totalVolume: points.reduce((sum, point) => sum + point.count, 0)
        }))
        .sort((a, b) => b.totalVolume - a.totalVolume)
        .slice(0, 7); // Show top 7 categories
    
    categoriesByVolume.forEach(({category, points}) => {
        const color = colors[colorIndex % colors.length];
        colorIndex++;
        
        datasets.push({
            label: category,
            data: points.map(point => ({
                x: point.date,
                y: point.count
            })),
            borderColor: color,
            backgroundColor: color + '20',
            fill: false,
            tension: 0.1
        });
    });
    
    charts.trends = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM DD'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

// Processing runs functions
async function refreshProcessingRuns() {
    try {
        const data = await fetchData('/api/stats/processing-runs?limit=10');
        
        const tableBody = document.getElementById('processing-runs-table');
        tableBody.innerHTML = '';
        
        if (data.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4">
                        <div class="empty-state">
                            <i class="bi bi-clock-history"></i>
                            <p class="mb-0">No processing runs found</p>
                        </div>
                    </td>
                </tr>
            `;
        } else {
            data.forEach(run => {
                const row = createProcessingRunRow(run);
                tableBody.appendChild(row);
            });
        }
        
    } catch (error) {
        console.error('Error refreshing processing runs:', error);
        const tableBody = document.getElementById('processing-runs-table');
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Error loading processing runs
                </td>
            </tr>
        `;
    }
}

function createProcessingRunRow(run) {
    const row = document.createElement('tr');
    
    const startedDate = new Date(run.started_at);
    const duration = run.duration_seconds ? formatDuration(run.duration_seconds) : '--';
    const status = run.success ? 'Success' : (run.completed_at ? 'Error' : 'Running');
    const statusClass = run.success ? 'run-success' : (run.completed_at ? 'run-error' : 'run-pending');
    
    row.innerHTML = `
        <td>
            <code class="small">${run.run_id.substring(0, 8)}...</code>
        </td>
        <td>${startedDate.toLocaleString()}</td>
        <td>${duration}</td>
        <td>${formatNumber(run.emails_processed || 0)}</td>
        <td>${formatNumber(run.emails_deleted || 0)}</td>
        <td>
            <span class="run-status ${statusClass}">
                ${status === 'Success' ? '<i class="bi bi-check-circle"></i>' : 
                  status === 'Error' ? '<i class="bi bi-x-circle"></i>' : 
                  '<i class="bi bi-clock"></i>'}
                ${status}
            </span>
        </td>
    `;
    
    // Add error message tooltip if available
    if (run.error_message) {
        row.setAttribute('title', run.error_message);
        row.setAttribute('data-bs-toggle', 'tooltip');
    }
    
    return row;
}

// Utility functions
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString();
}

function formatDuration(seconds) {
    if (!seconds || seconds < 1) return '< 1s';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength - 3) + '...' : text;
}

// Enhanced color generation with gradients and better palette
function generateEnhancedColors(count) {
    const baseColors = [
        '#0d6efd', '#198754', '#ffc107', '#dc3545', '#0dcaf0',
        '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d',
        '#495057', '#f8f9fa', '#e9ecef', '#dee2e6', '#adb5bd'
    ];
    
    const backgrounds = [];
    const borders = [];
    const hovers = [];
    
    for (let i = 0; i < count; i++) {
        const baseColor = baseColors[i % baseColors.length];
        
        backgrounds.push(baseColor);
        borders.push(baseColor);
        hovers.push(adjustBrightness(baseColor, -20)); // Darker on hover
    }
    
    return { backgrounds, borders, hovers };
}

// Utility function to adjust color brightness
function adjustBrightness(color, amount) {
    const usePound = color.charAt(0) === '#';
    const col = usePound ? color.slice(1) : color;
    const r = parseInt(col.substring(0, 2), 16);
    const g = parseInt(col.substring(2, 4), 16);
    const b = parseInt(col.substring(4, 6), 16);
    
    const adjustedR = Math.max(0, Math.min(255, r + amount));
    const adjustedG = Math.max(0, Math.min(255, g + amount));
    const adjustedB = Math.max(0, Math.min(255, b + amount));
    
    const adjustedColor = ((adjustedR << 16) | (adjustedG << 8) | adjustedB).toString(16).padStart(6, '0');
    return (usePound ? '#' : '') + adjustedColor;
}

// Generate simple color array for backward compatibility
function generateColors(count) {
    return generateEnhancedColors(count).backgrounds;
}

// Enhanced utility functions
function updateMetricWithAnimation(elementId, value) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Add loading class
    element.classList.add('loading-shimmer');
    
    setTimeout(() => {
        element.textContent = value;
        element.classList.remove('loading-shimmer');
        element.classList.add('fade-in');
    }, 300);
}

function getTrendIcon(trend) {
    switch (trend) {
        case 'up': return '<i class="bi bi-arrow-up"></i>';
        case 'down': return '<i class="bi bi-arrow-down"></i>';
        case 'stable': return '<i class="bi bi-arrow-right"></i>';
        default: return '<i class="bi bi-dash"></i>';
    }
}

function getTrendColor(trend) {
    switch (trend) {
        case 'up': return 'text-success';
        case 'down': return 'text-danger';
        case 'stable': return 'text-info';
        default: return 'text-muted';
    }
}

function getTrendDirection(value) {
    // Mock trend calculation - in real implementation, this would compare with historical data
    const random = Math.random();
    if (random > 0.6) return 'up';
    if (random < 0.3) return 'down';
    return 'stable';
}

function updateTrendIndicator(elementId, trend) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const icon = getTrendIcon(trend);
    const color = getTrendColor(trend);
    const text = trend === 'up' ? '↗ Trending Up' : 
                 trend === 'down' ? '↘ Trending Down' : 
                 '→ Stable';
    
    element.innerHTML = `${icon} ${text}`;
    element.className = `badge ${color.replace('text-', 'bg-').replace('bg-', 'bg-') + '-subtle'} ${color} small`;
}

function getEfficiencyBadgeClass(efficiency) {
    switch (efficiency) {
        case 'Excellent': return 'bg-success-subtle text-success';
        case 'Good': return 'bg-info-subtle text-info';
        case 'Average': return 'bg-warning-subtle text-warning';
        case 'Slow': return 'bg-danger-subtle text-danger';
        default: return 'bg-secondary-subtle text-secondary';
    }
}

function calculateEfficiency(metrics) {
    const totalEmails = metrics.total_processed || 0;
    const avgTime = metrics.avg_processing_seconds || 0;
    
    if (totalEmails === 0 || avgTime === 0) return 'N/A';
    
    // More sophisticated efficiency calculation
    const emailsPerSecond = avgTime > 0 ? 1 / avgTime : 0;
    const processingRate = totalEmails > 0 ? totalEmails / Math.max(1, avgTime) : 0;
    
    if (emailsPerSecond > 5 || processingRate > 100) return 'Excellent';
    if (emailsPerSecond > 2 || processingRate > 50) return 'Good';
    if (emailsPerSecond > 0.5 || processingRate > 10) return 'Average';
    return 'Slow';
}

// Category details modal (for future enhancement)
function showCategoryDetails(category) {
    console.log('Category details:', category);
    // Could show a modal with detailed category information
    showSuccess(`Clicked on category: ${category.name} (${formatNumber(category.count)} emails)`);
}

// Background execution time functions
async function fetchBackgroundExecutionTime() {
    try {
        const API_BASE_URL = 'http://192.168.1.162:8001'; // FastAPI service
        const response = await fetch(`${API_BASE_URL}/api/background/next-execution`);
        const data = await response.json();
        
        if (response.ok && !data.error) {
            return data;
        } else {
            console.warn('Background service not running or error:', data.error || 'Unknown error');
            return { error: data.error || 'Service unavailable', running: false };
        }
    } catch (error) {
        console.warn('Error fetching background execution time:', error);
        return { error: 'Connection failed', running: false };
    }
}

// Store next execution data globally for countdown updates
let nextExecutionData = null;
let countdownInterval = null;

function updateBackgroundExecutionDisplay(data) {
    const countdownEl = document.getElementById('next-execution-countdown');
    const timeEl = document.getElementById('next-execution-time');
    const statusBadgeEl = document.getElementById('background-status-badge');
    
    if (!countdownEl || !timeEl || !statusBadgeEl) {
        console.warn('Background execution display elements not found');
        return;
    }
    
    // Store the data globally for countdown updates
    nextExecutionData = data;
    
    if (data.error || !data.running) {
        countdownEl.textContent = '--';
        timeEl.textContent = data.error || 'Service stopped';
        statusBadgeEl.textContent = data.running === false ? 'Stopped' : 'Disabled';
        statusBadgeEl.className = 'badge bg-danger-subtle text-danger small';
        
        // Clear any existing countdown interval
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
        return;
    }
    
    // Display formatted next execution time (absolute time)
    if (data.next_execution_formatted) {
        // Parse UTC time and convert to local timezone
        const nextTime = new Date(data.next_execution + 'Z'); // Append 'Z' to indicate UTC
        const timeString = nextTime.toLocaleString('en-US', { 
            month: 'short',
            day: 'numeric',
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        timeEl.textContent = `${timeString}`;
    } else {
        timeEl.textContent = 'Calculating...';
    }
    
    // Update status badge
    statusBadgeEl.textContent = 'Running';
    statusBadgeEl.className = 'badge bg-success-subtle text-success small';
    
    // Start the real-time countdown
    startRealTimeCountdown(data);
}

function startRealTimeCountdown(data) {
    // Clear any existing countdown interval
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    const countdownEl = document.getElementById('next-execution-countdown');
    if (!countdownEl) return;
    
    // Parse UTC time correctly by appending 'Z'
    const nextExecution = new Date(data.next_execution + 'Z');
    
    // Update countdown immediately
    updateCountdownDisplay(nextExecution, countdownEl);
    
    // Update countdown every second
    countdownInterval = setInterval(() => {
        updateCountdownDisplay(nextExecution, countdownEl);
    }, 1000);
}

function updateCountdownDisplay(nextExecution, countdownEl) {
    const now = new Date();
    const timeDiff = nextExecution - now;
    
    if (timeDiff <= 0) {
        countdownEl.textContent = 'Running...';
        countdownEl.className = 'metric-value text-warning mb-1 fw-bold';
        return;
    }
    
    const totalSeconds = Math.floor(timeDiff / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    
    let displayText = '';
    let colorClass = 'metric-value text-secondary mb-1';
    
    if (hours > 0) {
        displayText = `${hours}h ${minutes}m ${seconds}s`;
    } else if (minutes > 0) {
        displayText = `${minutes}m ${seconds}s`;
        // Make it more prominent when under 1 hour
        colorClass = 'metric-value text-primary mb-1 fw-bold';
    } else {
        displayText = `${seconds}s`;
        // Make it urgent when under 1 minute
        colorClass = 'metric-value text-danger mb-1 fw-bold';
    }
    
    countdownEl.textContent = displayText;
    countdownEl.className = colorClass;
}

async function refreshBackgroundExecutionTime() {
    const data = await fetchBackgroundExecutionTime();
    updateBackgroundExecutionDisplay(data);
}

// Start background execution time updates
let backgroundExecutionInterval;

function startBackgroundExecutionUpdates() {
    // Initial load
    refreshBackgroundExecutionTime();
    
    // Update every 10 seconds
    backgroundExecutionInterval = setInterval(() => {
        refreshBackgroundExecutionTime();
    }, 10000);
}

function stopBackgroundExecutionUpdates() {
    if (backgroundExecutionInterval) {
        clearInterval(backgroundExecutionInterval);
        backgroundExecutionInterval = null;
    }
    
    // Also clear the countdown interval
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
}

// Export functions for global access
window.refreshDashboardData = refreshDashboardData;
window.refreshProcessingRuns = refreshProcessingRuns;
window.handleTabSwitch = handleAnalyticsTabSwitch; // Updated name
window.handleAnalyticsTabSwitch = handleAnalyticsTabSwitch;
window.refreshCategoriesData = refreshCategoriesData;
window.switchCategoriesView = switchCategoriesView;
window.renderCategoriesChart = renderCategoriesChart;
window.renderCategoriesColumns = renderCategoriesColumns;
window.fetchData = fetchData;
window.fetchAccountsData = fetchAccountsData;
window.deleteAccount = deleteAccount;
window.refreshBackgroundExecutionTime = refreshBackgroundExecutionTime;
window.startBackgroundExecutionUpdates = startBackgroundExecutionUpdates;
window.stopBackgroundExecutionUpdates = stopBackgroundExecutionUpdates;