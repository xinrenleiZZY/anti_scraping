// ASIN 分析大屏 JS
let chartInstances = {
    organicRank: null,
    price: null,
    rankingTrend: null
};

let tomSelectInstances = {};
let currentAsin = '';
let currentData = null;

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    initTomSelects();
    loadKeywordsForFilter();
    
    // ASIN 输入框回车查询
    document.getElementById('asinInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            loadAsinAnalysis();
        }
    });
    
    // 时间范围变化时自动刷新
    document.getElementById('dateRange').addEventListener('change', () => {
        if (currentAsin) loadAsinAnalysis();
    });
});

// 初始化 Tom Select
function initTomSelects() {
    tomSelectInstances.keyword = new TomSelect('#keywordFilter', {
        maxItems: null,
        placeholder: '选择关键词筛选...',
        plugins: ['remove_button', 'dropdown_input'],
        create: false,
        onChange: () => {
            if (currentAsin) loadAsinAnalysis();
        }
    });
}

// 加载关键词列表到筛选器
async function loadKeywordsForFilter() {
    try {
        const res = await apiFetch('/keywords');
        const keywords = Array.isArray(res) ? res : (res.keywords || []);
        
        if (tomSelectInstances.keyword) {
            tomSelectInstances.keyword.clearOptions();
            keywords.forEach(kw => {
                tomSelectInstances.keyword.addOption({ value: kw, text: kw });
            });
        }
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

// 加载 ASIN 分析数据
async function loadAsinAnalysis() {
    const asinInput = document.getElementById('asinInput');
    let asin = asinInput.value.trim().toUpperCase();
    
    if (!asin) {
        // 使用默认 ASIN
        asin = 'B0GFVBV9W7';
        asinInput.value = asin;
    }
    
    currentAsin = asin;
    const days = parseInt(document.getElementById('dateRange').value);
    const selectedKeywords = tomSelectInstances.keyword ? tomSelectInstances.keyword.getValue() : [];
    
    // 显示加载状态
    showLoading(true);
    
    try {
        // 构建请求参数
        let url = `/results/asin-analysis?asin=${encodeURIComponent(asin)}&days=${days}`;
        if (selectedKeywords && selectedKeywords.length > 0) {
            selectedKeywords.forEach(kw => url += `&keywords=${encodeURIComponent(kw)}`);
        }
        
        const data = await apiFetch(url);
        currentData = data;
        
        if (!data || !data.records || data.records.length === 0) {
            showEmptyData();
            return;
        }
        
        // 更新界面
        updateStatsCards(data);
        updateKeywordsList(data);
        updateCharts(data);
        updateDetailTable(data);
        
        // 显示内容
        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('statsCards').style.display = 'flex';
        document.getElementById('mainContent').style.display = 'block';
        
    } catch (error) {
        console.error('加载分析数据失败:', error);
        alert('加载失败: ' + error.message);
        showEmptyData();
    } finally {
        showLoading(false);
    }
}

// 更新统计卡片
function updateStatsCards(data) {
    const keywords = [...new Set(data.records.map(r => r.keyword))];
    document.getElementById('totalKeywords').textContent = keywords.length;
    
    const organicRanks = data.records.filter(r => r.organic_rank && r.organic_rank > 0).map(r => r.organic_rank);
    const avgRank = organicRanks.length > 0 ? (organicRanks.reduce((a, b) => a + b, 0) / organicRanks.length).toFixed(1) : '-';
    document.getElementById('avgRank').textContent = avgRank !== '-' ? `#${avgRank}` : '-';
    
    const latest = data.records.sort((a, b) => new Date(b.scraped_at) - new Date(a.scraped_at))[0];
    document.getElementById('currentPrice').textContent = latest.price_current ? formatPrice(latest.price_current) : '-';
    
    const prices = data.records.filter(r => r.price_current).map(r => parseFloat(r.price_current.replace(/[^0-9.-]/g, ''))).filter(p => !isNaN(p));
    if (prices.length > 0) {
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        document.getElementById('priceRange').textContent = `$${minPrice.toFixed(2)} - $${maxPrice.toFixed(2)}`;
    } else {
        document.getElementById('priceRange').textContent = '-';
    }
}

// 更新关键词列表
function updateKeywordsList(data) {
    const keywords = [...new Set(data.records.map(r => r.keyword))];
    const container = document.getElementById('keywordsList');
    
    container.innerHTML = keywords.map(kw => `
        <span class="keyword-tag" onclick="filterByKeyword('${escapeHtml(kw)}')">
            ${escapeHtml(kw.length > 40 ? kw.substring(0, 40) + '...' : kw)}
        </span>
    `).join('');
}

window.filterByKeyword = function(keyword) {
    if (tomSelectInstances.keyword) {
        tomSelectInstances.keyword.addItem(keyword);
    }
    loadAsinAnalysis();
};

// 更新图表
function updateCharts(data) {
    const sortedRecords = [...data.records].sort((a, b) => new Date(a.scraped_at) - new Date(b.scraped_at));
    
    const dates = [...new Set(sortedRecords.map(r => formatDate(r.scraped_at)))];
    const keywords = [...new Set(data.records.map(r => r.keyword))];
    
    // 整体自然排名趋势
    const avgRankByDate = {};
    sortedRecords.forEach(r => {
        const date = formatDate(r.scraped_at);
        if (r.organic_rank && r.organic_rank > 0) {
            if (!avgRankByDate[date]) avgRankByDate[date] = { sum: 0, count: 0 };
            avgRankByDate[date].sum += r.organic_rank;
            avgRankByDate[date].count++;
        }
    });
    
    const rankDates = Object.keys(avgRankByDate);
    const ranks = rankDates.map(date => (avgRankByDate[date].sum / avgRankByDate[date].count).toFixed(1));
    
    // 价格趋势
    const priceByDate = {};
    sortedRecords.forEach(r => {
        const date = formatDate(r.scraped_at);
        if (r.price_current) {
            const price = parseFloat(r.price_current.replace(/[^0-9.-]/g, ''));
            if (!isNaN(price)) {
                priceByDate[date] = price;
            }
        }
    });
    
    const priceDates = Object.keys(priceByDate);
    const prices = priceDates.map(date => priceByDate[date]);
    
    // 各关键词排名趋势
    const keywordRankData = {};
    keywords.forEach(kw => {
        keywordRankData[kw] = {};
        const kwRecords = sortedRecords.filter(r => r.keyword === kw && r.organic_rank && r.organic_rank > 0);
        kwRecords.forEach(r => {
            const date = formatDate(r.scraped_at);
            keywordRankData[kw][date] = r.organic_rank;
        });
    });
    
    updateOrganicRankChart(rankDates, ranks);
    updatePriceChart(priceDates, prices);
    updateRankingTrendChart(keywordRankData, rankDates);
}

// 更新自然排名图表
function updateOrganicRankChart(labels, data) {
    const ctx = document.getElementById('organicRankChart').getContext('2d');
    
    if (chartInstances.organicRank) {
        chartInstances.organicRank.destroy();
    }
    
    chartInstances.organicRank = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '平均自然排名',
                data: data,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top', labels: { color: '#94a3b8', font: { size: 10 } } },
                tooltip: { callbacks: { label: (ctx) => `排名: #${ctx.raw}` } }
            },
            scales: {
                y: { 
                    reverse: true, 
                    title: { display: true, text: '排名', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 } },
                    grid: { color: '#334155' }
                },
                x: { 
                    title: { display: true, text: '日期', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 },
                    grid: { color: '#334155' }
                }
            }
        }
    });
}

// 更新价格图表
function updatePriceChart(labels, data) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    if (chartInstances.price) {
        chartInstances.price.destroy();
    }
    
    chartInstances.price = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '价格 ($)',
                data: data,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#10b981',
                pointBorderColor: '#fff',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top', labels: { color: '#94a3b8', font: { size: 10 } } },
                tooltip: { callbacks: { label: (ctx) => `价格: $${ctx.raw}` } }
            },
            scales: {
                y: { 
                    title: { display: true, text: '价格 (USD)', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 }, callback: (v) => '$' + v },
                    grid: { color: '#334155' }
                },
                x: { 
                    title: { display: true, text: '日期', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 },
                    grid: { color: '#334155' }
                }
            }
        }
    });
}

// 更新各关键词排名趋势对比图
function updateRankingTrendChart(keywordRankData, allDates) {
    const ctx = document.getElementById('rankingTrendChart').getContext('2d');
    
    if (chartInstances.rankingTrend) {
        chartInstances.rankingTrend.destroy();
    }
    
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
    
    const datasets = Object.keys(keywordRankData).map((kw, idx) => {
        const data = allDates.map(date => keywordRankData[kw][date] || null);
        return {
            label: kw.length > 25 ? kw.substring(0, 25) + '...' : kw,
            data: data,
            borderColor: colors[idx % colors.length],
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            pointRadius: 2,
            pointBackgroundColor: colors[idx % colors.length],
            tension: 0.2,
            spanGaps: true
        };
    });
    
    chartInstances.rankingTrend = new Chart(ctx, {
        type: 'line',
        data: { labels: allDates, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 10 } },
                tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: #${ctx.raw}` } }
            },
            scales: {
                y: { 
                    reverse: true, 
                    title: { display: true, text: '排名', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 } },
                    grid: { color: '#334155' }
                },
                x: { 
                    title: { display: true, text: '日期', color: '#94a3b8', font: { size: 10 } },
                    ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 },
                    grid: { color: '#334155' }
                }
            }
        }
    });
}

// 更新详情表格
function updateDetailTable(data) {
    const tbody = document.getElementById('detailTableBody');
    const sorted = [...data.records].sort((a, b) => new Date(b.scraped_at) - new Date(a.scraped_at));
    
    tbody.innerHTML = sorted.map(r => `
        <tr>
            <td>${new Date(r.scraped_at).toLocaleString()} </td>
            <td><span class="badge bg-secondary" style="font-size: 10px;">${escapeHtml(r.keyword || '-')}</span></td>
            <td>${r.organic_rank ? '#' + r.organic_rank : '-'}</td>
            <td>${r.ad_rank || '-'}</td>
            <td class="text-success">${r.price_current || '-'}</td>
            <td>${r.rating_stars ? r.rating_stars + ' ★' : '-'}</td>
            <td>${r.rating_count ? r.rating_count.toLocaleString() : '-'}</td>
        </tr>
    `).join('');
}

// 辅助函数
function formatDate(isoString) {
    const d = new Date(isoString);
    return `${d.getMonth() + 1}/${d.getDate()}`;
}

function formatPrice(price) {
    if (!price) return '-';
    const match = price.match(/\d+\.?\d*/);
    if (match) return '$' + match[0];
    return price;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(show) {
    // 简单实现
}

function showEmptyData() {
    document.getElementById('emptyState').style.display = 'block';
    document.getElementById('statsCards').style.display = 'none';
    document.getElementById('mainContent').style.display = 'none';
}