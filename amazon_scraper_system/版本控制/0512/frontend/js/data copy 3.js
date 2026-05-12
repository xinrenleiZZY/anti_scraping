let currentPage = 1;
let totalPages = 1;
let usersData = [];
let selectedKeywords = [];
let selectedTags = [];
let allKeywords = [];
let allTags = [];
let allFestivals = [];
let allFestivalTypes = [];
let allHotSeasons = [];
let allAsins = [];
let keywordTagsMap = {};
let keywordFestivalMap = {};
let keywordFestivalTypeMap = {};
let keywordHotSeasonMap = {};
let keywordOwnerMap = {};

// ========== 列配置 ==========
const ALL_COLUMNS = [
    { key: 'id', label: 'ID', width: '60px', default: true, group: '基础信息' },
    { key: 'keyword', label: '关键词', width: '120px', default: true, group: '基础信息' },
    { key: 'asin', label: 'ASIN', width: '110px', default: true, group: '基础信息' },
    { key: 'title', label: '标题', width: '300px', default: true, group: '基础信息' },
    { key: 'url', label: '商品链接', width: '200px', default: false, group: '基础信息' },
    { key: 'price_current', label: '当前价格', width: '90px', default: true, group: '价格信息' },
    { key: 'price_list', label: '原价/划线价', width: '90px', default: false, group: '价格信息' },
    { key: 'rating_stars', label: '评分', width: '80px', default: true, group: '评分信息' },
    { key: 'rating_count', label: '评论数', width: '100px', default: true, group: '评分信息' },
    { key: 'page', label: '页码', width: '60px', default: false, group: '排名位置' },
    { key: 'data_index', label: '数据索引', width: '80px', default: false, group: '排名位置' },
    { key: 'index_position', label: '页面位置', width: '90px', default: false, group: '排名位置' },
    { key: 'ad_type', label: '广告类型', width: '100px', default: true, group: '排名位置' },
    { key: 'ad_rank', label: '广告排名', width: '90px', default: false, group: '排名位置' },
    { key: 'organic_rank', label: '自然排名', width: '90px', default: true, group: '排名位置' },
    { key: 'brand_name', label: '品牌', width: '120px', default: false, group: '商品属性' },
    { key: 'is_prime', label: 'Prime', width: '60px', default: false, group: '商品属性' },
    { key: 'image_small', label: '小图', width: '80px', default: false, group: '图片' },
    { key: 'image_large', label: '大图', width: '80px', default: false, group: '图片' },
    { key: 'inner_products', label: '内嵌商品', width: '200px', default: false, group: '内嵌商品' },
    { key: 'inner_products_count', label: '内嵌商品数', width: '100px', default: false, group: '内嵌商品' },
    { key: 'postal_code', label: '邮编', width: '80px', default: false, group: '地理位置' },
    { key: 'date', label: '日期', width: '100px', default: false, group: '时间戳' },
    { key: 'scraped_at', label: '抓取时间', width: '150px', default: true, group: '时间戳' },
    { key: 'created_at', label: '创建时间', width: '150px', default: false, group: '时间戳' },
    { key: 'updated_at', label: '更新时间', width: '150px', default: false, group: '时间戳' },
    { key: 'tags', label: '标签', width: '150px', default: false, group: '关键词属性' },
    { key: 'festival', label: '节日', width: '100px', default: false, group: '关键词属性' },
    { key: 'festival_type', label: '大/小节日', width: '100px', default: false, group: '关键词属性' },
    { key: 'hot_season', label: '热卖期', width: '100px', default: false, group: '关键词属性' },
    { key: 'owner', label: '负责人', width: '100px', default: false, group: '关键词属性' }
];

const DEFAULT_COLUMNS = [
    'keyword', 'asin', 'title', 'price_current', 'rating_stars', 'rating_count',
    'ad_type', 'ad_rank', 'organic_rank', 'page', 'scraped_at'
];

let visibleColumns = [];

function loadColumnSettings() {
    const saved = localStorage.getItem('data_visible_columns');
    if (saved) {
        visibleColumns = JSON.parse(saved);
    } else {
        visibleColumns = ALL_COLUMNS.filter(col => col.default).map(col => col.key);
    }
    renderColumnSettingsPanel();
}

function renderColumnSettingsPanel() {
    const container = document.getElementById('columnSettingsList');
    if (!container) return;
    
    const groups = {};
    ALL_COLUMNS.forEach(col => {
        const group = col.group || '其他';
        if (!groups[group]) groups[group] = [];
        groups[group].push(col);
    });
    
    let html = '';
    for (const [groupName, columns] of Object.entries(groups)) {
        html += `
            <div class="mt-3 mb-2">
                <h6 class="text-muted"><i class="bi bi-folder"></i> ${groupName}</h6>
                <div class="row">
                    ${columns.map(col => `
                        <div class="col-md-3 mb-2">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" 
                                       value="${col.key}" id="col_${col.key}"
                                       ${visibleColumns.includes(col.key) ? 'checked' : ''}>
                                <label class="form-check-label" for="col_${col.key}">
                                    <span class="badge bg-secondary">${col.label}</span>
                                </label>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <hr class="my-2">
        `;
    }
    container.innerHTML = html;
}

function selectAllColumns() {
    ALL_COLUMNS.forEach(col => {
        const cb = document.getElementById(`col_${col.key}`);
        if (cb) cb.checked = true;
    });
}

function deselectAllColumns() {
    ALL_COLUMNS.forEach(col => {
        const cb = document.getElementById(`col_${col.key}`);
        if (cb) cb.checked = false;
    });
}

function resetToDefaultColumns() {
    const defaultKeys = ALL_COLUMNS.filter(col => col.default).map(col => col.key);
    ALL_COLUMNS.forEach(col => {
        const cb = document.getElementById(`col_${col.key}`);
        if (cb) cb.checked = defaultKeys.includes(col.key);
    });
}

function saveColumnSettings() {
    visibleColumns = [];
    ALL_COLUMNS.forEach(col => {
        const cb = document.getElementById(`col_${col.key}`);
        if (cb && cb.checked) visibleColumns.push(col.key);
    });
    localStorage.setItem('data_visible_columns', JSON.stringify(visibleColumns));
    bootstrap.Modal.getInstance(document.getElementById('columnSettingsModal')).hide();
    searchData(currentPage);
}

function renderTableHeader() {
    const columns = visibleColumns.map(key => {
        const col = ALL_COLUMNS.find(c => c.key === key);
        return `<th>${col?.label || key}</th>`;
    }).join('');
    return `<tr>${columns}</tr>`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderTableRow(item) {
    const cells = visibleColumns.map(key => {
        let value = item[key];
        
        if (key === 'rating_stars' && value) value = `${value} ★`;
        else if (key === 'rating_count' && value) value = value.toLocaleString();
        else if (key === 'ad_type' && value) {
            const badgeClass = value === 'Organic' ? 'bg-success' : 
                              value === 'SP' ? 'bg-primary' : 
                              value === 'SB' ? 'bg-info text-dark' : 'bg-warning text-dark';
            return `<td><span class="badge ${badgeClass}">${value}</span></td>`;
        }
        else if (key === 'is_prime' && value === true) return `<td><i class="bi bi-check-lg text-primary"></i> Prime</td>`;
        else if (key === 'is_prime') return `<td>-</td>`;
        else if (key === 'title' && value) {
            const truncated = value.length > 50 ? value.substring(0, 50) + '...' : value;
            return `<td title="${escapeHtml(value)}" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(truncated)}</td>`;
        }
        else if (key === 'url' && value && value !== 'N/A') {
            return `<td><a href="${value}" target="_blank"><i class="bi bi-box-arrow-up-right"></i> 查看</a></table>`;
        }
        else if (key === 'url') return `<td>-</td>`;
        else if (key === 'asin' && value) {
            if (value.includes(',')) {
                const asins = value.split(',');
                const asinBadges = asins.map(a => `<code class="me-1">${a}</code>`).join('');
                return `<td>${asinBadges} <a href="https://www.amazon.com/dp/${asins[0]}" target="_blank"><i class="bi bi-box-arrow-up-right"></i></a><tr>`;
            }
            return `<td><code>${value}</code> <a href="https://www.amazon.com/dp/${value}" target="_blank"><i class="bi bi-box-arrow-up-right"></i></a></td>`;
        }
        else if (key === 'keyword' && value) return `<td><strong>${escapeHtml(value)}</strong></td>`;
        else if (key === 'inner_products_count' && value) {
            return value > 0 ? `<td><span class="badge bg-secondary">${value}个商品</span></td>` : `<td>-</td>`;
        }
        else if (key === 'inner_products' && value) {
            try {
                const products = Array.isArray(value) ? value : JSON.parse(value);
                if (products && products.length > 0) {
                    return `<td><span class="badge bg-secondary" style="cursor:pointer;" onclick='showInnerProductsModal(${JSON.stringify(products).replace(/'/g, "&#39;")})'>查看详情(${products.length})</span></td>`;
                }
            } catch(e) {}
            return `<td>-</td>`;
        }
        else if (key === 'image_small' && value) {
            return `<td><img src="${value}" style="width:40px; height:auto;" onerror="this.style.display='none'"></td>`;
        }
        else if (key === 'image_large' && value) return `<td><a href="${value}" target="_blank">查看大图</a></td>`;
        else if (key === 'brand_name' && value) return `<td><span class="text-muted">${escapeHtml(value)}</span></td>`;
        else if (key === 'index_position' && value) return `<td><code>${value}</code></td>`;
        else if ((key === 'created_at' || key === 'updated_at') && value) value = new Date(value).toLocaleString();
        else if (key === 'scraped_at' && value) value = new Date(value).toLocaleString();
        else if (key === 'date' && value) value = new Date(value).toLocaleDateString();
        else if (key === 'festival_type' && value) {
            const badgeClass = value === '大节日' ? 'tag-red' : 'tag-orange';
            return `<td><span class="tag ${badgeClass}">${value}</span></td>`;
        }
        else if (key === 'hot_season' && value) {
            const badgeClass = value === '高峰期' ? 'tag-red' : value === '预热期' ? 'tag-orange' : 'tag-gray';
            const icon = value === '高峰期' ? '🔥 ' : value === '预热期' ? '⏰ ' : '';
            return `<td><span class="tag ${badgeClass}">${icon}${value}</span></td>`;
        }
        else if (key === 'tags' && value) {
            if (Array.isArray(value)) {
                return `<td>${value.map(t => `<span class="tag tag-blue">${escapeHtml(t)}</span>`).join('') || '-'}</td>`;
            }
            return `<td>-</td>`;
        }
        else if (key === 'owner' && value) return `<td><span class="tag tag-purple">${escapeHtml(value)}</span></td>`;
        
        if (value === undefined || value === null || value === '') value = '-';
        if (typeof value === 'string') return `<td>${escapeHtml(value)}</td>`;
        return `<td>${value}</td>`;
    }).join('');
    return `</tr>${cells}</tr>`;
}

function showInnerProductsModal(products) {
    const modalHtml = `
        <div class="modal fade" id="innerProductsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="bi bi-box"></i> 内嵌商品详情</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="table-responsive">
                            <table class="table table-sm table-striped">
                                <thead><tr><th>位置</th><th>ASIN</th><th>标题</th><th>价格</th></tr></thead>
                                <tbody>
                                    ${products.map(p => `
                                        <tr>
                                            <td>${p.position}</td>
                                            <td><code>${p.asin || '-'}</code> <a href="https://www.amazon.com/dp/${p.asin}" target="_blank"><i class="bi bi-box-arrow-up-right"></i></a></td>
                                            <td style="max-width:400px;">${escapeHtml(p.title || '-')}</td>
                                            <td>${p.price || '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">关闭</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    const existingModal = document.getElementById('innerProductsModal');
    if (existingModal) existingModal.remove();
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = new bootstrap.Modal(document.getElementById('innerProductsModal'));
    modal.show();
    document.getElementById('innerProductsModal').addEventListener('hidden.bs.modal', function() { this.remove(); });
}

// ========== API 数据加载 ==========
async function loadUsers() {
    try {
        usersData = await apiFetch('/users');
        const select = document.getElementById('filterUser');
        if (select) {
            select.innerHTML = '<option value="">全部人员</option>' +
                usersData.map(u => `<option value="${u.id}">${escapeHtml(u.name)}</option>`).join('');
        }
    } catch (e) {
        console.error('加载人员失败:', e);
    }
}

async function loadKeywords() {
    try {
        const res = await apiFetch('/keywords');
        allKeywords = Array.isArray(res) ? res : (res.keywords || []);
        const select = document.getElementById('filterKeyword');
        if (select) {
            select.innerHTML = '<option value="">全部关键词</option>' +
                allKeywords.map(kw => `<option value="${escapeHtml(kw)}">${escapeHtml(kw)}</option>`).join('');
        }
    } catch (error) {
        console.error('加载关键词失败:', error);
    }
}

async function loadAsinOptions() {
    try {
        const result = await apiFetch('/results?limit=500');
        allAsins = [...new Set((result.data || []).map(item => item.asin).filter(a => a))];
        const select = document.getElementById('filterAsin');
        if (select) {
            select.innerHTML = '<option value="">全部ASIN</option>' + 
                allAsins.slice(0, 100).map(asin => `<option value="${asin}">${asin}</option>`).join('');
        }
    } catch (error) {
        console.error('加载ASIN列表失败:', error);
    }
}

// ========== 从后端加载所有筛选选项 ==========
async function loadFilterOptionsFromBackend() {
    try {
        // 1. 获取所有关键词
        const keywordsRes = await apiFetch('/keywords');
        const keywords = Array.isArray(keywordsRes) ? keywordsRes : (keywordsRes.keywords || []);
        
        // 2. 并行获取每个关键词的标签、节日等信息
        const promises = keywords.map(async (kw) => {
            try {
                const [tags, festival, festivalType, hotSeason] = await Promise.all([
                    apiFetch(`/keywords/${encodeURIComponent(kw)}/tags`).catch(() => []),
                    apiFetch(`/keywords/${encodeURIComponent(kw)}/festival`).catch(() => ''),
                    apiFetch(`/keywords/${encodeURIComponent(kw)}/festival-type`).catch(() => ''),
                    apiFetch(`/keywords/${encodeURIComponent(kw)}/hot-season`).catch(() => '')
                ]);
                keywordTagsMap[kw] = Array.isArray(tags) ? tags : [];
                keywordFestivalMap[kw] = festival || '';
                keywordFestivalTypeMap[kw] = festivalType || '';
                keywordHotSeasonMap[kw] = hotSeason || '';
            } catch(e) {
                console.warn(`获取关键词 ${kw} 信息失败:`, e);
            }
        });
        await Promise.all(promises);
        
        // 3. 收集所有标签（去重）
        const tagsSet = new Set();
        Object.values(keywordTagsMap).forEach(tags => {
            tags.forEach(t => tagsSet.add(t));
        });
        allTags = Array.from(tagsSet).sort();
        
        // 4. 收集所有节日（去重）
        const festivalsSet = new Set();
        Object.values(keywordFestivalMap).forEach(f => {
            if (f) festivalsSet.add(f);
        });
        allFestivals = Array.from(festivalsSet).sort();
        
        // 5. 收集所有大/小节日类型（去重）
        const festivalTypesSet = new Set();
        Object.values(keywordFestivalTypeMap).forEach(ft => {
            if (ft) festivalTypesSet.add(ft);
        });
        allFestivalTypes = Array.from(festivalTypesSet).sort();
        
        // 6. 收集所有热卖期类型（去重）
        const hotSeasonsSet = new Set();
        Object.values(keywordHotSeasonMap).forEach(hs => {
            if (hs) hotSeasonsSet.add(hs);
        });
        allHotSeasons = Array.from(hotSeasonsSet).sort();
        
        // 7. 渲染UI
        renderMultiSelectOptions();
        renderFestivalSelects();
        
        console.log('筛选选项加载完成:', {
            tags: allTags.length,
            festivals: allFestivals.length,
            festivalTypes: allFestivalTypes.length,
            hotSeasons: allHotSeasons.length
        });
        
    } catch (error) {
        console.error('加载筛选选项失败:', error);
    }
}

function renderMultiSelectOptions() {
    // 关键词多选框
    const keywordContainer = document.getElementById('keywordOptions');
    if (keywordContainer) {
        keywordContainer.innerHTML = allKeywords.map(kw => `
            <label class="multi-select-option">
                <input type="checkbox" value="${escapeHtml(kw)}" onchange="toggleKeywordSelection('${escapeHtml(kw)}', this.checked)">
                <span>${escapeHtml(kw)}</span>
            </label>
        `).join('');
    }
    
    // 标签多选框
    const tagContainer = document.getElementById('tagOptions');
    if (tagContainer) {
        tagContainer.innerHTML = allTags.map(tag => `
            <label class="multi-select-option">
                <input type="checkbox" value="${escapeHtml(tag)}" onchange="toggleTagSelection('${escapeHtml(tag)}', this.checked)">
                <span>${escapeHtml(tag)}</span>
            </label>
        `).join('');
    }
}

function renderFestivalSelects() {
    const festivalSelect = document.getElementById('filterFestival');
    if (festivalSelect) {
        festivalSelect.innerHTML = '<option value="">全部节日</option>' + 
            allFestivals.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join('');
    }
    
    const festivalTypeSelect = document.getElementById('filterFestivalType');
    if (festivalTypeSelect) {
        festivalTypeSelect.innerHTML = '<option value="">全部类型</option>' + 
            allFestivalTypes.map(ft => `<option value="${escapeHtml(ft)}">${escapeHtml(ft)}</option>`).join('');
    }
    
    const hotSeasonSelect = document.getElementById('filterHotSeason');
    if (hotSeasonSelect) {
        hotSeasonSelect.innerHTML = '<option value="">全部热卖期</option>' + 
            allHotSeasons.map(hs => `<option value="${escapeHtml(hs)}">${hs === '高峰期' ? '🔥 ' : hs === '预热期' ? '⏰ ' : ''}${escapeHtml(hs)}</option>`).join('');
    }
}

// ========== 筛选逻辑 ==========
window.toggleKeywordSelection = function(keyword, isChecked) {
    if (isChecked) {
        if (!selectedKeywords.includes(keyword)) selectedKeywords.push(keyword);
    } else {
        selectedKeywords = selectedKeywords.filter(k => k !== keyword);
    }
    updateKeywordButtonText();
};

window.toggleTagSelection = function(tag, isChecked) {
    if (isChecked) {
        if (!selectedTags.includes(tag)) selectedTags.push(tag);
    } else {
        selectedTags = selectedTags.filter(t => t !== tag);
    }
    updateTagButtonText();
};

function updateKeywordButtonText() {
    const btn = document.getElementById('keywordSelectedText');
    if (btn) btn.innerText = selectedKeywords.length ? `已选 ${selectedKeywords.length} 个` : '选择关键词';
}

function updateTagButtonText() {
    const btn = document.getElementById('tagSelectedText');
    if (btn) btn.innerText = selectedTags.length ? `已选 ${selectedTags.length} 个` : '选择标签';
}

window.toggleKeywordDropdown = function() {
    document.getElementById('keywordDropdown')?.classList.toggle('show');
};

window.toggleTagDropdown = function() {
    document.getElementById('tagDropdown')?.classList.toggle('show');
};

window.onUserChange = function() {
    const userId = document.getElementById('filterUser').value;
    const kwSelect = document.getElementById('filterKeyword');
    if (!userId) { loadKeywords(); return; }
    const user = usersData.find(u => u.id == userId);
    const keywords = user ? user.keywords : [];
    kwSelect.innerHTML = '<option value="">全部关键词</option>' +
        keywords.map(kw => `<option value="${escapeHtml(kw)}">${escapeHtml(kw)}</option>`).join('');
    searchData(1);
};

// ========== 搜索数据 ==========
window.searchData = async function(page = 1) {
    currentPage = page;
    const userId = document.getElementById('filterUser').value;
    const keyword = document.getElementById('filterKeyword').value;
    const asin = document.getElementById('filterAsin').value;
    const adType = document.getElementById('filterAdType').value;
    const dateFrom = document.getElementById('filterDateFrom').value;
    const dateTo = document.getElementById('filterDateTo').value;
    const festival = document.getElementById('filterFestival')?.value;
    const festivalType = document.getElementById('filterFestivalType')?.value;
    const hotSeason = document.getElementById('filterHotSeason')?.value;
    
    const params = new URLSearchParams({ page: currentPage, limit: 50 });
    
    if (selectedKeywords.length > 0) {
        selectedKeywords.forEach(kw => params.append('keywords', kw));
    } else if (keyword) {
        params.append('keyword', keyword);
    }
    
    if (userId && !keyword && selectedKeywords.length === 0) {
        const user = usersData.find(u => u.id == userId);
        if (user?.keywords?.length) {
            user.keywords.forEach(kw => params.append('keywords', kw));
        }
    }
    
    if (selectedTags.length > 0) selectedTags.forEach(tag => params.append('tags', tag));
    if (asin) params.append('asin', asin);
    if (adType) params.append('ad_type', adType);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (festival) params.append('festival', festival);
    if (festivalType) params.append('festival_type', festivalType);
    if (hotSeason) params.append('hot_season', hotSeason);
    
    try {
        const result = await apiFetch(`/results?${params}`);
        const tbody = document.getElementById('dataTableBody');
        const thead = document.querySelector('#dataTable thead');
        
        if (visibleColumns.length === 0) loadColumnSettings();
        if (thead) thead.innerHTML = renderTableHeader();
        
        if (result.data && result.data.length > 0) {
            tbody.innerHTML = result.data.map(item => renderTableRow(item)).join('');
            totalPages = result.total_pages || 1;
            renderPagination();
        } else {
            const colSpan = visibleColumns.length || 10;
            tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center">暂无数据</td></table>`;
        }
    } catch (error) {
        console.error('加载数据失败:', error);
        document.getElementById('dataTableBody').innerHTML = `<table><td colspan="13" class="text-center text-danger">加载失败</td></tr>`;
    }
};

function renderPagination() {
    const container = document.getElementById('paginationContainer');
    if (!container) return;
    
    let buttonsHtml = `
        <button class="page-btn" onclick="searchData(1)" ${currentPage === 1 ? 'disabled' : ''}><i class="bi bi-chevron-double-left"></i></button>
        <button class="page-btn" onclick="searchData(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}><i class="bi bi-chevron-left"></i></button>
    `;
    
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    startPage = Math.max(1, endPage - 4);
    
    for (let i = startPage; i <= endPage; i++) {
        buttonsHtml += `<button class="page-btn ${currentPage === i ? 'active' : ''}" onclick="searchData(${i})">${i}</button>`;
    }
    
    buttonsHtml += `
        <button class="page-btn" onclick="searchData(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}><i class="bi bi-chevron-right"></i></button>
        <button class="page-btn" onclick="searchData(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}><i class="bi bi-chevron-double-right"></i></button>
    `;
    
    container.innerHTML = `
        <div class="pagination-buttons">${buttonsHtml}</div>
        <div class="page-info">第 ${currentPage} / ${totalPages} 页</div>
        <div class="pagination-jump">
            <span class="text-muted small">跳转到</span>
            <input type="number" id="jumpPage" min="1" max="${totalPages}">
            <button onclick="jumpToPage()">跳转</button>
        </div>
    `;
    
    const jumpInput = document.getElementById('jumpPage');
    if (jumpInput) jumpInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') jumpToPage(); });
}

window.jumpToPage = function() {
    const val = parseInt(document.getElementById('jumpPage')?.value);
    if (val >= 1 && val <= totalPages) searchData(val);
};

window.resetFilters = function() {
    document.getElementById('filterUser').value = '';
    selectedKeywords = [];
    selectedTags = [];
    updateKeywordButtonText();
    updateTagButtonText();
    document.querySelectorAll('#keywordOptions input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#tagOptions input').forEach(cb => cb.checked = false);
    document.getElementById('filterAsin').value = '';
    document.getElementById('filterAdType').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    if (document.getElementById('filterFestival')) document.getElementById('filterFestival').value = '';
    if (document.getElementById('filterFestivalType')) document.getElementById('filterFestivalType').value = '';
    if (document.getElementById('filterHotSeason')) document.getElementById('filterHotSeason').value = '';
    loadKeywords();
    searchData(1);
};

window.exportData = function() {
    const params = new URLSearchParams();
    const keyword = document.getElementById('filterKeyword').value;
    const asin = document.getElementById('filterAsin').value;
    const adType = document.getElementById('filterAdType').value;
    if (keyword) params.append('keyword', keyword);
    if (asin) params.append('asin', asin);
    if (adType) params.append('ad_type', adType);
    const url = `${API_BASE}/results/export?${params.toString()}`;
    window.open(url, '_blank');
};

// ========== ASIN 输入联想 ==========
async function initAsinAutocomplete() {
    const asinInput = document.getElementById('filterAsin');
    const asinDropdown = document.getElementById('asinAutocomplete');
    if (!asinInput || !asinDropdown) return;
    
    try {
        const result = await apiFetch('/results?limit=2000');
        allAsins = [...new Set((result.data || []).map(item => item.asin).filter(a => a))];
        
        asinInput.addEventListener('input', function() {
            const value = this.value.toUpperCase();
            if (!value) { asinDropdown.classList.remove('show'); return; }
            const filtered = allAsins.filter(asin => asin && asin.toUpperCase().includes(value));
            if (filtered.length) {
                asinDropdown.innerHTML = filtered.map(asin => 
                    `<div class="autocomplete-item" onclick="selectAsin('${asin}')">${escapeHtml(asin)}</div>`
                ).join('');
                asinDropdown.classList.add('show');
            } else {
                asinDropdown.classList.remove('show');
            }
        });
    } catch (error) {
        console.error('加载ASIN列表失败:', error);
    }
}

window.selectAsin = function(asin) {
    document.getElementById('filterAsin').value = asin;
    document.getElementById('asinAutocomplete').classList.remove('show');
};

// ========== 页面初始化 ==========
document.addEventListener('DOMContentLoaded', async () => {
    loadUsers();
    loadKeywords();
    loadAsinOptions();
    loadColumnSettings();
    await loadFilterOptionsFromBackend();
    await initAsinAutocomplete();
    searchData(1);
});

// ========== 全局点击事件 ==========
document.addEventListener('click', function(e) {
    const keywordMultiSelect = document.getElementById('keywordMultiSelect');
    const keywordDropdown = document.getElementById('keywordDropdown');
    if (keywordDropdown && keywordMultiSelect && !keywordMultiSelect.contains(e.target)) {
        keywordDropdown.classList.remove('show');
    }
    const tagMultiSelect = document.getElementById('tagMultiSelect');
    const tagDropdown = document.getElementById('tagDropdown');
    if (tagDropdown && tagMultiSelect && !tagMultiSelect.contains(e.target)) {
        tagDropdown.classList.remove('show');
    }
    const asinContainer = document.querySelector('.autocomplete-container');
    const asinDropdown = document.getElementById('asinAutocomplete');
    if (asinDropdown && asinContainer && !asinContainer.contains(e.target)) {
        asinDropdown.classList.remove('show');
    }
});