// API 基础地址（使用相对路径，nginx 会代理）
const API_BASE = '/api';

// 或者直接使用完整地址（如果 nginx 不配置代理）
// const API_BASE = 'http://localhost:8000/api';

async function checkApiStatus() {
    try {
        // 使用相对路径，通过 nginx 代理
        const response = await fetch('/health');
        const statusEl = document.getElementById('api-status');
        if (response.ok) {
            statusEl.textContent = 'API 在线';
            statusEl.className = 'badge bg-success';
        } else {
            throw new Error();
        }
    } catch (error) {
        const statusEl = document.getElementById('api-status');
        statusEl.textContent = 'API 离线';
        statusEl.className = 'badge bg-danger';
    }
}

async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Error: ${url}`, error);
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    checkApiStatus();
});