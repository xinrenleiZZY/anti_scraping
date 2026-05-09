let asinSelectInstance;
let selectedAsins = [];
let chartInstances = {};
let allData = [];

// 可用图表配置
const AVAILABLE_CHARTS = [
    { id: 'rankTrend', label: '排名趋势对比', enabled: true, grid: 2, order: 0 },
    { id: 'priceComparison', label: '价格对比', enabled: true, grid: 3, order: 1 },
    { id: 'ratingComparison', label: '评分对比', enabled: true, grid: 3, order: 2 },
    { id: 'keywordDistribution', label: '关键词分布TOP10', enabled: true, grid: 2, order: 3 },
    { id: 'adTypeDistribution', label: '广告类型分布', enabled: true, grid: 3, order: 4 },
    { id: 'rankDistribution', label: '排名区间分布', enabled: true, grid: 3, order: 5 },
    { id: 'priceHistory', label: '价格历史趋势', enabled: false, grid: 2, order: 6 },
    { id: 'reviewCountTrend', label: '评论数趋势', enabled: false, grid: 2, order: 7 },
    { id: 'organicVsAd', label: '自然vs广告对比', enabled: false, grid: 3, order: 8 },
    { id: 'pageDistribution', label: '页码分布', enabled: false, grid: 3, order: 9 },
    { id: 'primeDistribution', label: 'Prime商品占比', enabled: false, grid: 3, order: 10 },
    { id: 'brandComparison', label: '品牌对比TOP10', enabled: false, grid: 2, order: 11 },
    { id: 'avgRankByKeyword', label: '关键词平均排名', enabled: false, grid: 2, order: 12 },
    { id: 'timeHeatmap', label: '时间热力分布', enabled: false, grid: 1, order: 13 },
    { id: 'competitorAnalysis', label: '竞品分析矩阵', enabled: false, grid: 1, order: 14 }
];

// 预设模板
const CHART_TEMPLATES = {
    template1: {
        name: '经典分析模板',
        charts: [
            { id: 'rankTrend', enabled: true, grid: 1, order: 0 },
            { id: 'priceComparison', enabled: true, grid: 3, order: 1 },
            { id: 'ratingComparison', enabled: true, grid: 3, order: 2 },
            { id: 'adTypeDistribution', enabled: true, grid: 3, order: 3 },
            { id: 'keywordDistribution', enabled: true, grid: 2, order: 4 },
            { id: 'rankDistribution', enabled: true, grid: 2, order: 5 }
        ]
    },
    template2: {
        name: '竞品对比模板',
        charts: [
            { id: 'competitorAnalysis', enabled: true, grid: 1, order: 0 },
            { id: 'rankTrend', enabled: true, grid: 2, order: 1 },
            { id: 'priceHistory', enabled: true, grid: 2, order: 2 },
            { id: 'brandComparison', enabled: true, grid: 2, order: 3 },
            { id: 'avgRankByKeyword', enabled: true, grid: 2, order: 4 },
            { id: 'primeDistribution', enabled: true, grid: 3, order: 5 },
            { id: 'pageDistribution', enabled: true, grid: 3, order: 6 },
            { id: 'organicVsAd', enabled: true, grid: 3, order: 7 }
        ]
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    loadChartSettings();
    initAsinSelect();
    renderChartOptions();
    await loadAsinOptions();
});

// 初始化ASIN选择器
function initAsinSelect() {
    asinSelectInstance = new TomSelect('#asinSelect', {
        maxItems: 5,
        plugins: ['remove_button'],
        create: true,
        placeholder: '输入或选择ASIN...',
        onChange: (values) => {
            selectedAsins = values;
            updateSelectedAsinsBadges();
            loadData();
        }
    });
}

// 加载ASIN选项
async function loadAsinOptions() {
    try {
        const result = await apiFetch('/results?limit=500&page=1');
        const asins = [...new Set((result.data || []).map(item => item.asin).filter(a => a))];
        asins.forEach(asin => {
            asinSelectInstance.addOption({ value: asin, text: asin });
        });
    } catch (error) {
        console.error('加载ASIN失败:', error);
    }
}

// 更新选中的ASIN徽章
function updateSelectedAsinsBadges() {
    const container = document.getElementById('selectedAsins');
    if (selectedAsins.length === 0) {
        container.innerHTML = '<span class="text-white-50 small">请选择ASIN进行分析</span>';
        return;
    }
    container.innerHTML = selectedAsins.map(asin => `
        <span class="asin-badge">
            ${asin}
            <span class="remove-btn" onclick="removeAsin('${asin}')">×</span>
        </span>
    `).join('');
}

// 移除ASIN
function removeAsin(asin) {
    asinSelectInstance.removeItem(asin);
}

// 加载数据
async function loadData() {
    if (selectedAsins.length === 0) {
        document.getElementById('chartsContainer').innerHTML = '<div class="text-center text-white-50 py-5">请选择ASIN开始分析</div>';
        updateStats({ total: 0, avgRank: 0, keywords: 0 });
        return;
    }

    try {
        const days = document.getElementById('dateRange').value;
        const dateFrom = new Date();
        dateFrom.setDate(dateFrom.getDate() - days);

        // 为每个ASIN分别请求数据
        allData = [];
        for (const asin of selectedAsins) {
            const params = new URLSearchParams({
                asin: asin,
                limit: 500,
                page: 1,
                date_from: dateFrom.toISOString().split('T')[0]
            });

            const result = await apiFetch(`/results?${params}`);
            if (result.data) {
                allData = allData.concat(result.data);
            }
        }

        updateStats({
            total: allData.length,
            avgRank: calculateAvgRank(allData),
            keywords: new Set(allData.map(d => d.keyword)).size
        });

        renderCharts();
    } catch (error) {
        console.error('加载数据失败:', error);
    }
}

// 更新统计卡片
function updateStats(stats) {
    document.getElementById('statTotalRecords').textContent = stats.total.toLocaleString();
    document.getElementById('statAvgRank').textContent = stats.avgRank > 0 ? stats.avgRank.toFixed(1) : '-';
    document.getElementById('statKeywords').textContent = stats.keywords;
}

// 计算平均排名
function calculateAvgRank(data) {
    const ranks = data.map(d => d.organic_rank || d.ad_rank).filter(r => r);
    return ranks.length > 0 ? ranks.reduce((a, b) => a + b, 0) / ranks.length : 0;
}

// 渲染图表选项
function renderChartOptions() {
    const container = document.getElementById('chartOptions');
    const sortedCharts = [...AVAILABLE_CHARTS].sort((a, b) => a.order - b.order);

    container.innerHTML = sortedCharts.map(chart => `
        <div class="chart-option">
            <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <button class="btn btn-sm" style="padding: 0 4px; font-size: 10px; line-height: 1; background: #475569; border: none; color: #cbd5e1;"
                            onclick="moveChartUp('${chart.id}')" title="上移">▲</button>
                    <button class="btn btn-sm" style="padding: 0 4px; font-size: 10px; line-height: 1; background: #475569; border: none; color: #cbd5e1;"
                            onclick="moveChartDown('${chart.id}')" title="下移">▼</button>
                </div>
                <label style="flex: 1; margin: 0;">
                    <input type="checkbox" class="form-check-input me-2"
                           id="chart_${chart.id}"
                           ${chart.enabled ? 'checked' : ''}
                           onchange="toggleChart('${chart.id}')">
                    ${chart.label}
                </label>
            </div>
            <select class="form-select form-select-sm" style="width: 80px; background: #475569; border-color: #64748b; color: #f1f5f9;"
                    onchange="changeChartGrid('${chart.id}', this.value)">
                <option value="1" ${chart.grid === 1 ? 'selected' : ''}>全宽</option>
                <option value="2" ${chart.grid === 2 ? 'selected' : ''}>1/2</option>
                <option value="3" ${chart.grid === 3 ? 'selected' : ''}>1/3</option>
            </select>
        </div>
    `).join('');
}

// 切换图表显示
function toggleChart(chartId) {
    const chart = AVAILABLE_CHARTS.find(c => c.id === chartId);
    if (chart) {
        chart.enabled = !chart.enabled;
        saveChartSettings();
        renderCharts();
    }
}

// 改变图表网格
function changeChartGrid(chartId, grid) {
    const chart = AVAILABLE_CHARTS.find(c => c.id === chartId);
    if (chart) {
        chart.grid = parseInt(grid);
        saveChartSettings();
        renderCharts();
    }
}

// 应用模板
function applyTemplate(templateKey) {
    const template = CHART_TEMPLATES[templateKey];
    if (!template) return;

    // 先禁用所有图表
    AVAILABLE_CHARTS.forEach(c => c.enabled = false);

    // 应用模板配置
    template.charts.forEach(tc => {
        const chart = AVAILABLE_CHARTS.find(c => c.id === tc.id);
        if (chart) {
            chart.enabled = tc.enabled;
            chart.grid = tc.grid;
            chart.order = tc.order;
        }
    });

    saveChartSettings();
    renderChartOptions();
    renderCharts();
}

// 初始化拖拽排序
function initDragSort() {
    let draggedElement = null;

    document.querySelectorAll('.chart-container').forEach(container => {
        container.addEventListener('dragstart', function(e) {
            draggedElement = this;
            this.style.opacity = '0.5';
        });

        container.addEventListener('dragend', function(e) {
            this.style.opacity = '';
        });

        container.addEventListener('dragover', function(e) {
            e.preventDefault();
        });

        container.addEventListener('drop', function(e) {
            e.preventDefault();
            if (draggedElement !== this) {
                const draggedId = draggedElement.dataset.chartId;
                const targetId = this.dataset.chartId;

                const draggedChart = AVAILABLE_CHARTS.find(c => c.id === draggedId);
                const targetChart = AVAILABLE_CHARTS.find(c => c.id === targetId);

                if (draggedChart && targetChart) {
                    const tempOrder = draggedChart.order;
                    draggedChart.order = targetChart.order;
                    targetChart.order = tempOrder;

                    saveChartSettings();
                    renderCharts();
                }
            }
        });
    });
}

// 上移图表
function moveChartUp(chartId) {
    const chart = AVAILABLE_CHARTS.find(c => c.id === chartId);
    if (!chart || chart.order === 0) return;

    const prevChart = AVAILABLE_CHARTS.find(c => c.order === chart.order - 1);
    if (prevChart) {
        prevChart.order++;
        chart.order--;
        saveChartSettings();
        renderChartOptions();
        renderCharts();
    }
}

// 下移图表
function moveChartDown(chartId) {
    const chart = AVAILABLE_CHARTS.find(c => c.id === chartId);
    const maxOrder = Math.max(...AVAILABLE_CHARTS.map(c => c.order));
    if (!chart || chart.order === maxOrder) return;

    const nextChart = AVAILABLE_CHARTS.find(c => c.order === chart.order + 1);
    if (nextChart) {
        nextChart.order--;
        chart.order++;
        saveChartSettings();
        renderChartOptions();
        renderCharts();
    }
}

// 全选图表
function selectAllCharts() {
    AVAILABLE_CHARTS.forEach(chart => {
        chart.enabled = true;
        const checkbox = document.getElementById(`chart_${chart.id}`);
        if (checkbox) checkbox.checked = true;
    });
    saveChartSettings();
    renderCharts();
}

// 全不选图表
function deselectAllCharts() {
    AVAILABLE_CHARTS.forEach(chart => {
        chart.enabled = false;
        const checkbox = document.getElementById(`chart_${chart.id}`);
        if (checkbox) checkbox.checked = false;
    });
    saveChartSettings();
    renderCharts();
}

// 保存图表设置
function saveChartSettings() {
    localStorage.setItem('dashboard_chart_settings', JSON.stringify(AVAILABLE_CHARTS));
}

// 加载图表设置
function loadChartSettings() {
    const saved = localStorage.getItem('dashboard_chart_settings');
    if (saved) {
        const settings = JSON.parse(saved);
        settings.forEach(s => {
            const chart = AVAILABLE_CHARTS.find(c => c.id === s.id);
            if (chart) chart.enabled = s.enabled;
        });
    }
}

// 切换设置面板
function toggleSettings() {
    document.getElementById('settingsPanel').classList.toggle('active');
    document.getElementById('settingsOverlay').classList.toggle('active');
}

// 渲染所有图表
function renderCharts() {
    const container = document.getElementById('chartsContainer');

    // 销毁旧图表
    Object.values(chartInstances).forEach(chart => chart.destroy());
    chartInstances = {};

    if (allData.length === 0) {
        container.innerHTML = '<div class="text-center text-white-50 py-5">暂无数据</div>';
        return;
    }

    const enabledCharts = AVAILABLE_CHARTS.filter(c => c.enabled).sort((a, b) => a.order - b.order);

    let html = '';
    let currentRow = [];
    let currentRowWidth = 0;

    enabledCharts.forEach(chart => {
        const gridWidth = chart.grid; // 1=全宽, 2=半宽, 3=三分之一
        const colWidth = gridWidth === 1 ? 12 : gridWidth === 2 ? 6 : 4;

        // 如果当前行放不下，先输出当前行
        if (currentRowWidth + colWidth > 12) {
            html += `<div class="row mb-3">${currentRow.join('')}</div>`;
            currentRow = [];
            currentRowWidth = 0;
        }

        // 添加到当前行
        currentRow.push(`
            <div class="col-md-${colWidth}">
                <div class="chart-container" draggable="true" data-chart-id="${chart.id}">
                    <div class="chart-title">
                        <span>${chart.label}</span>
                        <span class="drag-handle" style="cursor: move; opacity: 0.5;">⋮⋮</span>
                    </div>
                    <canvas id="chart_${chart.id}" class="chart-canvas"></canvas>
                </div>
            </div>
        `);
        currentRowWidth += colWidth;

        // 如果当前行满了，输出
        if (currentRowWidth >= 12) {
            html += `<div class="row mb-3">${currentRow.join('')}</div>`;
            currentRow = [];
            currentRowWidth = 0;
        }
    });

    // 输出剩余的行
    if (currentRow.length > 0) {
        html += `<div class="row mb-3">${currentRow.join('')}</div>`;
    }

    container.innerHTML = html;

    // 渲染各个图表
    enabledCharts.forEach(chart => {
        const renderFunc = chartRenderers[chart.id];
        if (renderFunc) renderFunc();
    });

    // 初始化拖拽排序
    initDragSort();
}

// 图表渲染器
const chartRenderers = {
    rankTrend: () => {
        const data = {};
        selectedAsins.forEach(asin => {
            const asinData = allData.filter(d => d.asin === asin).sort((a, b) =>
                new Date(a.scraped_at) - new Date(b.scraped_at)
            );
            data[asin] = {
                dates: asinData.map(d => new Date(d.scraped_at).toLocaleDateString()),
                ranks: asinData.map(d => d.organic_rank || d.ad_rank || null)
            };
        });

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

        chartInstances.rankTrend = new Chart(document.getElementById('chart_rankTrend'), {
            type: 'line',
            data: {
                labels: data[selectedAsins[0]]?.dates || [],
                datasets: selectedAsins.map((asin, i) => ({
                    label: asin,
                    data: data[asin]?.ranks || [],
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { reverse: true, ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    priceComparison: () => {
        const prices = {};
        selectedAsins.forEach(asin => {
            const asinData = allData.filter(d => d.asin === asin);
            const priceValues = asinData.map(d => parseFloat((d.price_current || '0').replace(/[^0-9.]/g, ''))).filter(p => p > 0);
            prices[asin] = priceValues.length > 0 ? (priceValues.reduce((a, b) => a + b) / priceValues.length).toFixed(2) : 0;
        });

        chartInstances.priceComparison = new Chart(document.getElementById('chart_priceComparison'), {
            type: 'bar',
            data: {
                labels: selectedAsins,
                datasets: [{
                    label: '平均价格 ($)',
                    data: selectedAsins.map(asin => prices[asin]),
                    backgroundColor: '#3b82f6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    ratingComparison: () => {
        const ratings = {};
        selectedAsins.forEach(asin => {
            const asinData = allData.filter(d => d.asin === asin && d.rating_stars);
            ratings[asin] = asinData.length > 0 ? (asinData.reduce((a, b) => a + parseFloat(b.rating_stars), 0) / asinData.length).toFixed(1) : 0;
        });

        chartInstances.ratingComparison = new Chart(document.getElementById('chart_ratingComparison'), {
            type: 'radar',
            data: {
                labels: selectedAsins,
                datasets: [{
                    label: '平均评分',
                    data: selectedAsins.map(asin => ratings[asin]),
                    backgroundColor: '#3b82f620',
                    borderColor: '#3b82f6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        min: 0,
                        max: 5,
                        ticks: { color: '#cbd5e1', stepSize: 1 },
                        grid: { color: '#334155' },
                        pointLabels: { color: '#cbd5e1' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    keywordDistribution: () => {
        const keywords = {};
        allData.forEach(d => {
            keywords[d.keyword] = (keywords[d.keyword] || 0) + 1;
        });

        const sorted = Object.entries(keywords).sort((a, b) => b[1] - a[1]).slice(0, 10);

        chartInstances.keywordDistribution = new Chart(document.getElementById('chart_keywordDistribution'), {
            type: 'bar',
            data: {
                labels: sorted.map(k => k[0]),
                datasets: [{
                    label: '出现次数',
                    data: sorted.map(k => k[1]),
                    backgroundColor: '#10b981'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    adTypeDistribution: () => {
        const adTypes = {};
        allData.forEach(d => {
            adTypes[d.ad_type || 'Unknown'] = (adTypes[d.ad_type || 'Unknown'] || 0) + 1;
        });

        chartInstances.adTypeDistribution = new Chart(document.getElementById('chart_adTypeDistribution'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(adTypes),
                datasets: [{
                    data: Object.values(adTypes),
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    rankDistribution: () => {
        const rankRanges = { '1-10': 0, '11-20': 0, '21-50': 0, '51-100': 0, '100+': 0 };
        allData.forEach(d => {
            const rank = d.organic_rank || d.ad_rank;
            if (!rank) return;
            if (rank <= 10) rankRanges['1-10']++;
            else if (rank <= 20) rankRanges['11-20']++;
            else if (rank <= 50) rankRanges['21-50']++;
            else if (rank <= 100) rankRanges['51-100']++;
            else rankRanges['100+']++;
        });

        chartInstances.rankDistribution = new Chart(document.getElementById('chart_rankDistribution'), {
            type: 'pie',
            data: {
                labels: Object.keys(rankRanges),
                datasets: [{
                    data: Object.values(rankRanges),
                    backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    priceHistory: () => {
        const data = {};
        selectedAsins.forEach(asin => {
            const asinData = allData.filter(d => d.asin === asin).sort((a, b) =>
                new Date(a.scraped_at) - new Date(b.scraped_at)
            );
            data[asin] = {
                dates: asinData.map(d => new Date(d.scraped_at).toLocaleDateString()),
                prices: asinData.map(d => parseFloat((d.price_current || '0').replace(/[^0-9.]/g, '')) || null)
            };
        });

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

        chartInstances.priceHistory = new Chart(document.getElementById('chart_priceHistory'), {
            type: 'line',
            data: {
                labels: data[selectedAsins[0]]?.dates || [],
                datasets: selectedAsins.map((asin, i) => ({
                    label: asin,
                    data: data[asin]?.prices || [],
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    reviewCountTrend: () => {
        const data = {};
        selectedAsins.forEach(asin => {
            const asinData = allData.filter(d => d.asin === asin).sort((a, b) =>
                new Date(a.scraped_at) - new Date(b.scraped_at)
            );
            data[asin] = {
                dates: asinData.map(d => new Date(d.scraped_at).toLocaleDateString()),
                counts: asinData.map(d => d.rating_count || 0)
            };
        });

        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

        chartInstances.reviewCountTrend = new Chart(document.getElementById('chart_reviewCountTrend'), {
            type: 'line',
            data: {
                labels: data[selectedAsins[0]]?.dates || [],
                datasets: selectedAsins.map((asin, i) => ({
                    label: asin,
                    data: data[asin]?.counts || [],
                    borderColor: colors[i],
                    backgroundColor: colors[i] + '20',
                    tension: 0.3
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    organicVsAd: () => {
        const data = { organic: 0, ad: 0 };
        allData.forEach(d => {
            if (d.ad_type === 'Organic') data.organic++;
            else data.ad++;
        });

        chartInstances.organicVsAd = new Chart(document.getElementById('chart_organicVsAd'), {
            type: 'bar',
            data: {
                labels: ['自然排名', '广告排名'],
                datasets: [{
                    label: '数量',
                    data: [data.organic, data.ad],
                    backgroundColor: ['#10b981', '#3b82f6']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    pageDistribution: () => {
        const pages = {};
        allData.forEach(d => {
            const page = d.page || 1;
            pages[page] = (pages[page] || 0) + 1;
        });

        chartInstances.pageDistribution = new Chart(document.getElementById('chart_pageDistribution'), {
            type: 'bar',
            data: {
                labels: Object.keys(pages).sort((a, b) => a - b),
                datasets: [{
                    label: '商品数量',
                    data: Object.keys(pages).sort((a, b) => a - b).map(p => pages[p]),
                    backgroundColor: '#3b82f6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    primeDistribution: () => {
        const prime = allData.filter(d => d.is_prime).length;
        const nonPrime = allData.length - prime;

        chartInstances.primeDistribution = new Chart(document.getElementById('chart_primeDistribution'), {
            type: 'doughnut',
            data: {
                labels: ['Prime', '非Prime'],
                datasets: [{
                    data: [prime, nonPrime],
                    backgroundColor: ['#3b82f6', '#64748b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    brandComparison: () => {
        const brands = {};
        allData.forEach(d => {
            if (d.brand_name) {
                brands[d.brand_name] = (brands[d.brand_name] || 0) + 1;
            }
        });

        const sorted = Object.entries(brands).sort((a, b) => b[1] - a[1]).slice(0, 10);

        chartInstances.brandComparison = new Chart(document.getElementById('chart_brandComparison'), {
            type: 'bar',
            data: {
                labels: sorted.map(b => b[0]),
                datasets: [{
                    label: '出现次数',
                    data: sorted.map(b => b[1]),
                    backgroundColor: '#8b5cf6'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    avgRankByKeyword: () => {
        const kwRanks = {};
        allData.forEach(d => {
            if (!kwRanks[d.keyword]) kwRanks[d.keyword] = [];
            const rank = d.organic_rank || d.ad_rank;
            if (rank) kwRanks[d.keyword].push(rank);
        });

        const avgRanks = Object.entries(kwRanks).map(([kw, ranks]) => ({
            keyword: kw,
            avg: ranks.reduce((a, b) => a + b, 0) / ranks.length
        })).sort((a, b) => a.avg - b.avg).slice(0, 10);

        chartInstances.avgRankByKeyword = new Chart(document.getElementById('chart_avgRankByKeyword'), {
            type: 'bar',
            data: {
                labels: avgRanks.map(k => k.keyword),
                datasets: [{
                    label: '平均排名',
                    data: avgRanks.map(k => k.avg),
                    backgroundColor: '#f59e0b'
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { reverse: true, ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    timeHeatmap: () => {
        const canvas = document.getElementById('chart_timeHeatmap');
        const ctx = canvas.getContext('2d');

        // 简化热力图：按日期统计数据量
        const dateCounts = {};
        allData.forEach(d => {
            const date = new Date(d.scraped_at).toLocaleDateString();
            dateCounts[date] = (dateCounts[date] || 0) + 1;
        });

        const sorted = Object.entries(dateCounts).sort((a, b) => new Date(a[0]) - new Date(b[0]));

        chartInstances.timeHeatmap = new Chart(canvas, {
            type: 'line',
            data: {
                labels: sorted.map(d => d[0]),
                datasets: [{
                    label: '数据量',
                    data: sorted.map(d => d[1]),
                    borderColor: '#ef4444',
                    backgroundColor: '#ef444420',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } },
                    x: { ticks: { color: '#cbd5e1' }, grid: { color: '#334155' } }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    },

    competitorAnalysis: () => {
        // 竞品分析：对比各ASIN的关键指标
        const analysis = selectedAsins.map(asin => {
            const asinData = allData.filter(d => d.asin === asin);
            const ranks = asinData.map(d => d.organic_rank || d.ad_rank).filter(r => r);
            const prices = asinData.map(d => parseFloat((d.price_current || '0').replace(/[^0-9.]/g, ''))).filter(p => p > 0);
            const ratings = asinData.map(d => d.rating_stars).filter(r => r);

            return {
                asin,
                avgRank: ranks.length > 0 ? (ranks.reduce((a, b) => a + b, 0) / ranks.length).toFixed(1) : 0,
                avgPrice: prices.length > 0 ? (prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2) : 0,
                avgRating: ratings.length > 0 ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : 0,
                count: asinData.length
            };
        });

        chartInstances.competitorAnalysis = new Chart(document.getElementById('chart_competitorAnalysis'), {
            type: 'radar',
            data: {
                labels: ['平均排名(反)', '平均价格', '平均评分', '数据量'],
                datasets: analysis.map((item, i) => ({
                    label: item.asin,
                    data: [
                        100 - parseFloat(item.avgRank),
                        parseFloat(item.avgPrice),
                        parseFloat(item.avgRating) * 20,
                        item.count / 10
                    ],
                    borderColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][i],
                    backgroundColor: ['#3b82f620', '#10b98120', '#f59e0b20', '#ef444420', '#8b5cf620'][i]
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        ticks: { color: '#cbd5e1' },
                        grid: { color: '#334155' },
                        pointLabels: { color: '#cbd5e1' }
                    }
                },
                plugins: {
                    legend: { labels: { color: '#cbd5e1' } }
                }
            }
        });
    }
};

// 监听时间范围变化
document.getElementById('dateRange')?.addEventListener('change', loadData);
