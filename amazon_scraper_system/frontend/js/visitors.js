async function loadVisitorStats() {
    try {
        const data = await apiFetch('/visitor/stats');
        document.getElementById('statToday').textContent = data.today;
        document.getElementById('statWeek').textContent = data.week;
        document.getElementById('statTotal').textContent = data.total;

        document.getElementById('topPages').innerHTML = data.top_pages.length
            ? data.top_pages.map((p, i) => `
                <div class="d-flex justify-content-between py-1 border-bottom">
                    <span><span class="badge bg-secondary me-2">#${i+1}</span>${p.page}</span>
                    <span class="text-muted">${p.count} 次</span>
                </div>`).join('')
            : '<div class="text-muted">暂无数据</div>';

        const recent = await apiFetch('/visitor/recent?limit=50');
        document.getElementById('recentTable').innerHTML = recent.length
            ? recent.map(l => `
                <tr>
                    <td class="text-muted small">${l.visited_at ? l.visited_at.slice(5,16).replace('T',' ') : ''}</td>
                    <td>${l.page}</td>
                    <td class="text-muted small">${l.ip}</td>
                </tr>`).join('')
            : '<tr><td colspan="3" class="text-center text-muted">暂无访客</td></tr>';
    } catch (e) {
        console.error('加载访客数据失败:', e);
    }
}

document.addEventListener('DOMContentLoaded', loadVisitorStats);
