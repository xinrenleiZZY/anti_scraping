const RANK_LABELS = {
    organic_rank: '自然排名', ad_rank_sp: 'SP广告排名',
    ad_rank_sb: 'SB品牌广告排名', ad_rank_video: '视频广告排名'
};

async function loadTasks() {
    const tasks = await apiFetch('/asin-monitor/tasks');
    const container = document.getElementById('taskList');
    if (!tasks.length) {
        container.innerHTML = '<div class="col-12 text-center text-muted py-5"><i class="bi bi-bell-slash display-4"></i><p class="mt-2">暂无监控任务，点击右上角新增</p></div>';
        return;
    }
    container.innerHTML = tasks.map(t => {
        const nextRun = t.next_run ? new Date(t.next_run).toLocaleString() : '-';
        const lastRun = t.last_run ? new Date(t.last_run).toLocaleString() : '从未执行';
        const rankBadges = t.rank_types.map(r => `<span class="badge bg-secondary me-1">${RANK_LABELS[r] || r}</span>`).join('');
        return `
        <div class="col-md-6 col-lg-4">
            <div class="card h-100 ${t.enabled ? '' : 'opacity-50'}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge ${t.enabled ? 'bg-success' : 'bg-secondary'} me-2">${t.enabled ? '运行中' : '已停用'}</span>
                        <strong>${escapeHtml(t.asin)}</strong>
                    </div>
                    <div class="d-flex gap-1">
                        <button class="btn btn-sm btn-outline-primary" onclick="runNow('${t.id}')" title="立即执行"><i class="bi bi-play-fill"></i></button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="openEditModal(${JSON.stringify(t).replace(/"/g, '&quot;')})" title="编辑"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteTask('${t.id}')" title="删除"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
                <div class="card-body small">
                    <div class="mb-1"><i class="bi bi-person text-primary"></i> 监控人：<strong>${escapeHtml(t.monitor_name)}</strong></div>
                    <div class="mb-1"><i class="bi bi-clock text-warning"></i> 间隔：每 ${t.interval_hours} 小时 | 分析近 ${t.days} 天</div>
                    <div class="mb-2">${rankBadges}</div>
                    <div class="text-muted">上次：${lastRun}</div>
                    <div class="text-muted">下次：${nextRun}</div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function openAddModal() {
    document.getElementById('taskModalTitle').textContent = '新增监控任务';
    document.getElementById('editTaskId').value = '';
    document.getElementById('taskAsin').value = '';
    document.getElementById('taskMonitorName').value = '';
    document.getElementById('taskInterval').value = '4';
    document.getElementById('taskDays').value = '30';
    document.querySelectorAll('.rank-check').forEach(c => c.checked = false);
    document.getElementById('rankAll').checked = false;
    new bootstrap.Modal(document.getElementById('taskModal')).show();
}

window.openEditModal = function(t) {
    document.getElementById('taskModalTitle').textContent = '编辑监控任务';
    document.getElementById('editTaskId').value = t.id;
    document.getElementById('taskAsin').value = t.asin;
    document.getElementById('taskMonitorName').value = t.monitor_name;
    document.getElementById('taskInterval').value = t.interval_hours;
    document.getElementById('taskDays').value = t.days;
    document.querySelectorAll('.rank-check').forEach(c => { c.checked = t.rank_types.includes(c.value); });
    document.getElementById('rankAll').checked = document.querySelectorAll('.rank-check').length === t.rank_types.length;
    new bootstrap.Modal(document.getElementById('taskModal')).show();
};

window.toggleAllRanks = function(cb) {
    document.querySelectorAll('.rank-check').forEach(c => c.checked = cb.checked);
};

window.saveTask = async function() {
    const id = document.getElementById('editTaskId').value;
    const asin = document.getElementById('taskAsin').value.trim();
    const monitor_name = document.getElementById('taskMonitorName').value.trim();
    const interval_hours = parseFloat(document.getElementById('taskInterval').value);
    const days = parseInt(document.getElementById('taskDays').value);
    const rank_types = [...document.querySelectorAll('.rank-check:checked')].map(c => c.value);

    if (!asin) { alert('请输入ASIN'); return; }
    if (!monitor_name) { alert('请输入监控人名称'); return; }
    if (!rank_types.length) { alert('请至少选择一种排名类型'); return; }
    if (interval_hours < 2) { alert('查询间隔不得少于2小时'); return; }

    const body = { asin, monitor_name, rank_types, interval_hours, days };
    if (id) {
        await apiFetch(`/asin-monitor/tasks/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
        await apiFetch('/asin-monitor/tasks', { method: 'POST', body: JSON.stringify(body) });
    }
    bootstrap.Modal.getInstance(document.getElementById('taskModal')).hide();
    loadTasks();
};

window.deleteTask = async function(id) {
    if (!confirm('确定删除该监控任务？')) return;
    await apiFetch(`/asin-monitor/tasks/${id}`, { method: 'DELETE' });
    loadTasks();
};

window.runNow = async function(id) {
    const btn = event.currentTarget;
    btn.disabled = true;
    try {
        const res = await apiFetch(`/asin-monitor/tasks/${id}/run`, { method: 'POST' });
        alert('执行完成，飞书消息已发送');
        loadTasks();
    } catch(e) {
        alert('执行失败: ' + e.message);
    } finally {
        btn.disabled = false;
    }
};

function escapeHtml(t) {
    const d = document.createElement('div'); d.textContent = t; return d.innerHTML;
}

document.addEventListener('DOMContentLoaded', loadTasks);
