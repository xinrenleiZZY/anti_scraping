// ASIN 分析大屏 JS
let chartInstances = {
    organicRank: null, adRank: null, videoAdRank: null, sbAdRank: null,
    rankCompare: null, price: null, rankingTrend: null, adRankTrend: null, adType: null
};

let tomSelectInstances = {};
let currentAsin = '';
let currentData = null;

// 页面初始化
document.addEventListener('DOMContentLoaded', () => {
    initTomSelects();
    loadKeywordsForFilter();
    
    // 从 URL 参数读取 ASIN
    const urlAsin = new URLSearchParams(location.search).get('asin');
    if (urlAsin) {
        document.getElementById('asinInput').value = urlAsin.toUpperCase();
        loadAsinAnalysis();
    }

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

    const organicRanks = data.records.filter(r => r.organic_rank > 0).map(r => r.organic_rank);
    const avgRank = organicRanks.length > 0 ? (organicRanks.reduce((a,b)=>a+b,0)/organicRanks.length).toFixed(1) : '-';
    document.getElementById('avgRank').textContent = avgRank !== '-' ? `#${avgRank}` : '-';

    const spRanks = data.records.filter(r => r.ad_type === 'SP' && r.ad_rank > 0).map(r => r.ad_rank);
    document.getElementById('avgAdRank').textContent = spRanks.length > 0 ? `#${(spRanks.reduce((a,b)=>a+b,0)/spRanks.length).toFixed(1)}` : '-';

    const videoRanks = data.records.filter(r => r.ad_type === 'SB_Video' && r.ad_rank > 0).map(r => r.ad_rank);
    document.getElementById('avgVideoRank').textContent = videoRanks.length > 0 ? `#${(videoRanks.reduce((a,b)=>a+b,0)/videoRanks.length).toFixed(1)}` : '-';

    const latest = data.records.sort((a,b) => new Date(b.scraped_at)-new Date(a.scraped_at))[0];
    document.getElementById('currentPrice').textContent = latest.price_current ? formatPrice(latest.price_current) : '-';

    const prices = data.records.filter(r=>r.price_current).map(r=>parseFloat(r.price_current.replace(/[^0-9.-]/g,''))).filter(p=>!isNaN(p));
    if (prices.length > 0) {
        document.getElementById('priceRange').textContent = `$${Math.min(...prices).toFixed(2)}-$${Math.max(...prices).toFixed(2)}`;
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
    const sorted = [...data.records].sort((a,b) => new Date(a.scraped_at)-new Date(b.scraped_at));
    const allDates = [...new Set(sorted.map(r => formatDate(r.scraped_at)))];
    const keywords = [...new Set(data.records.map(r => r.keyword))];

    // 按日期聚合各类排名均值
    function avgByDate(records, rankField) {
        const map = {};
        records.forEach(r => {
            const d = formatDate(r.scraped_at);
            const v = r[rankField];
            if (v && v > 0) {
                if (!map[d]) map[d] = { sum: 0, count: 0 };
                map[d].sum += v; map[d].count++;
            }
        });
        return map;
    }

    // 1. 自然排名
    const organicMap = avgByDate(sorted, 'organic_rank');
    const organicDates = Object.keys(organicMap);
    updateRankChart('organicRankChart', 'organicRank', organicDates,
        organicDates.map(d => (organicMap[d].sum/organicMap[d].count).toFixed(1)),
        '平均自然排名', '#3b82f6', true);

    // 2. SP广告排名
    const spRecords = sorted.filter(r => r.ad_type === 'SP');
    const spMap = avgByDate(spRecords, 'ad_rank');
    const spDates = Object.keys(spMap);
    updateRankChart('adRankChart', 'adRank', spDates,
        spDates.map(d => (spMap[d].sum/spMap[d].count).toFixed(1)),
        '平均SP广告排名', '#f59e0b', true);

    // 3. SB_Video视频广告排名
    const videoRecords = sorted.filter(r => r.ad_type === 'SB_Video');
    const videoMap = avgByDate(videoRecords, 'ad_rank');
    const videoDates = Object.keys(videoMap);
    updateRankChart('videoAdRankChart', 'videoAdRank', videoDates,
        videoDates.map(d => (videoMap[d].sum/videoMap[d].count).toFixed(1)),
        '平均视频广告排名', '#ef4444', true);

    // 4. SB品牌广告排名
    const sbRecords = sorted.filter(r => r.ad_type === 'SB');
    const sbMap = avgByDate(sbRecords, 'ad_rank');
    const sbDates = Object.keys(sbMap);
    updateRankChart('sbAdRankChart', 'sbAdRank', sbDates,
        sbDates.map(d => (sbMap[d].sum/sbMap[d].count).toFixed(1)),
        '平均SB品牌广告排名', '#8b5cf6', true);

    // 5. 自然排名 vs 广告排名对比（双线）
    updateRankCompareChart(allDates, organicMap, spMap);

    // 6. 价格趋势
    const priceMap = {};
    sorted.forEach(r => {
        const d = formatDate(r.scraped_at);
        if (r.price_current) {
            const p = parseFloat(r.price_current.replace(/[^0-9.-]/g,''));
            if (!isNaN(p)) priceMap[d] = p;
        }
    });
    const priceDates = Object.keys(priceMap);
    updatePriceChart(priceDates, priceDates.map(d => priceMap[d]));

    // 7. 各关键词自然排名对比
    const kwOrganicData = {};
    keywords.forEach(kw => {
        kwOrganicData[kw] = {};
        sorted.filter(r => r.keyword === kw && r.organic_rank > 0).forEach(r => {
            kwOrganicData[kw][formatDate(r.scraped_at)] = r.organic_rank;
        });
    });
    updateRankingTrendChart(kwOrganicData, allDates);

    // 8. 各关键词SP广告排名对比
    const kwAdData = {};
    keywords.forEach(kw => {
        kwAdData[kw] = {};
        sorted.filter(r => r.keyword === kw && r.ad_type === 'SP' && r.ad_rank > 0).forEach(r => {
            kwAdData[kw][formatDate(r.scraped_at)] = r.ad_rank;
        });
    });
    updateAdRankTrendChart(kwAdData, allDates);

    // 9. 广告类型分布饼图
    const typeCounts = {};
    sorted.forEach(r => {
        const t = r.ad_type || '自然';
        typeCounts[t] = (typeCounts[t] || 0) + 1;
    });
    updateAdTypeChart(typeCounts);
}

// 通用排名折线图
function updateRankChart(canvasId, instanceKey, labels, data, label, color, reversed) {
    if (chartInstances[instanceKey]) chartInstances[instanceKey].destroy();
    if (!labels.length) { chartInstances[instanceKey] = null; return; }
    const ctx = document.getElementById(canvasId).getContext('2d');
    chartInstances[instanceKey] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [{ label, data, borderColor: color, backgroundColor: color.replace(')', ',0.1)').replace('rgb','rgba'), borderWidth: 2, pointRadius: 3, pointBackgroundColor: color, tension: 0.3, fill: true }] },
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { labels: { color: '#94a3b8', font: { size: 10 } } }, tooltip: { callbacks: { label: c => `排名: #${c.raw}` } } },
            scales: {
                y: { reverse: reversed, ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#334155' } }
            }
        }
    });
}

// 自然排名 vs 广告排名对比
function updateRankCompareChart(allDates, organicMap, spMap) {
    if (chartInstances.rankCompare) chartInstances.rankCompare.destroy();
    const ctx = document.getElementById('rankCompareChart').getContext('2d');
    chartInstances.rankCompare = new Chart(ctx, {
        type: 'line',
        data: { labels: allDates, datasets: [
            { label: '自然排名', data: allDates.map(d => organicMap[d] ? (organicMap[d].sum/organicMap[d].count).toFixed(1) : null), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 2, pointRadius: 2, tension: 0.3, fill: false, spanGaps: true },
            { label: 'SP广告排名', data: allDates.map(d => spMap[d] ? (spMap[d].sum/spMap[d].count).toFixed(1) : null), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', borderWidth: 2, pointRadius: 2, tension: 0.3, fill: false, spanGaps: true }
        ]},
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { labels: { color: '#94a3b8', font: { size: 10 } } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: #${c.raw}` } } },
            scales: {
                y: { reverse: true, ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#334155' } }
            }
        }
    });
}

// 各关键词SP广告排名对比
function updateAdRankTrendChart(kwAdData, allDates) {
    if (chartInstances.adRankTrend) chartInstances.adRankTrend.destroy();
    const colors = ['#f59e0b','#ef4444','#10b981','#3b82f6','#8b5cf6','#ec4899','#06b6d4','#84cc16'];
    const datasets = Object.keys(kwAdData).map((kw, i) => ({
        label: kw.length > 25 ? kw.substring(0,25)+'...' : kw,
        data: allDates.map(d => kwAdData[kw][d] || null),
        borderColor: colors[i % colors.length], backgroundColor: 'transparent',
        borderWidth: 1.5, pointRadius: 2, tension: 0.2, spanGaps: true
    }));
    const ctx = document.getElementById('adRankTrendChart').getContext('2d');
    chartInstances.adRankTrend = new Chart(ctx, {
        type: 'line',
        data: { labels: allDates, datasets },
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 10 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: #${c.raw}` } } },
            scales: {
                y: { reverse: true, ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#334155' } }
            }
        }
    });
}

// 广告类型分布饼图
function updateAdTypeChart(typeCounts) {
    if (chartInstances.adType) chartInstances.adType.destroy();
    const labels = Object.keys(typeCounts);
    const ctx = document.getElementById('adTypeChart').getContext('2d');
    chartInstances.adType = new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: labels.map(l => typeCounts[l]), backgroundColor: ['#3b82f6','#f59e0b','#ef4444','#8b5cf6','#10b981'], borderWidth: 0 }] },
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 10 } } } }
        }
    });
}

// 更新自然排名图表（保留旧接口）
function updateOrganicRankChart(labels, data) {
    updateRankChart('organicRankChart', 'organicRank', labels, data, '平均自然排名', '#3b82f6', true);
}

// 更新价格图表
function updatePriceChart(labels, data) {
    if (chartInstances.price) chartInstances.price.destroy();
    const ctx = document.getElementById('priceChart').getContext('2d');
    chartInstances.price = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [{ label: '价格 ($)', data, borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,0.1)', borderWidth: 2, pointRadius: 3, tension: 0.3, fill: true }] },
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { labels: { color: '#94a3b8', font: { size: 10 } } }, tooltip: { callbacks: { label: c => `价格: $${c.raw}` } } },
            scales: {
                y: { ticks: { color: '#94a3b8', font: { size: 9 }, callback: v => '$'+v }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#334155' } }
            }
        }
    });
}

// 更新各关键词自然排名趋势对比图
function updateRankingTrendChart(keywordRankData, allDates) {
    if (chartInstances.rankingTrend) chartInstances.rankingTrend.destroy();
    const colors = ['#3b82f6','#ef4444','#10b981','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#84cc16'];
    const datasets = Object.keys(keywordRankData).map((kw, i) => ({
        label: kw.length > 25 ? kw.substring(0,25)+'...' : kw,
        data: allDates.map(d => keywordRankData[kw][d] || null),
        borderColor: colors[i % colors.length], backgroundColor: 'transparent',
        borderWidth: 1.5, pointRadius: 2, tension: 0.2, spanGaps: true
    }));
    const ctx = document.getElementById('rankingTrendChart').getContext('2d');
    chartInstances.rankingTrend = new Chart(ctx, {
        type: 'line',
        data: { labels: allDates, datasets },
        options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 10 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: #${c.raw}` } } },
            scales: {
                y: { reverse: true, ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: '#334155' } },
                x: { ticks: { color: '#94a3b8', font: { size: 9 }, maxRotation: 45 }, grid: { color: '#334155' } }
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