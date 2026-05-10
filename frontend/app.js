const API_BASE = "";

let currentQuery = "";
let currentType = null;
let currentPage = 1;
const PAGE_SIZE = 20;

// DOM elements
const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const resultsEl = document.getElementById("results");
const statsEl = document.getElementById("stats");
const paginationEl = document.getElementById("pagination");
const filterButtons = document.querySelectorAll(".filter-bar button");

// === Event listeners ===
searchBtn.addEventListener("click", () => doSearch(1));
searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch(1);
});

filterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        filterButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentType = btn.dataset.type || null;
        doSearch(1);
    });
});

// === Core search ===
async function doSearch(page) {
    currentPage = page;

    // If no query and no filter, show homepage
    const q = searchInput.value.trim();
    if (!q && !currentType) {
        renderHome();
        return;
    }

    currentQuery = q;
    resultsEl.innerHTML = '<div class="loading">搜索中...</div>';
    paginationEl.innerHTML = "";

    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (currentType) params.set("resource_type", currentType);
    params.set("page", page);
    params.set("page_size", PAGE_SIZE);

    try {
        const resp = await fetch(`${API_BASE}/api/search?${params}`);
        if (!resp.ok) throw new Error("搜索请求失败");
        const data = await resp.json();
        renderResults(data);
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">⚠️</div>
            <p>搜索出错：${err.message}</p>
            <p style="margin-top:8px;font-size:13px">请确认后端服务已启动</p>
        </div>`;
    }
}

function renderResults(data) {
    // Stats
    statsEl.textContent = data.total > 0
        ? `共找到 ${data.total} 个资源`
        : "";

    if (data.results.length === 0) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">🔍</div>
            <p>没有找到相关资源</p>
            <p style="margin-top:8px;font-size:13px;color:#94a3b8">试试其他关键词</p>
        </div>`;
        paginationEl.innerHTML = "";
        return;
    }

    resultsEl.innerHTML = data.results.map((r) => `
        <div class="resource-card">
            <h3><a href="${escapeHtml(r.url)}" target="_blank" rel="noopener">${escapeHtml(r.title)}</a></h3>
            <div class="meta">
                <span class="badge badge-${r.resource_type}">${typeLabel(r.resource_type)}</span>
                ${r.tags ? r.tags.split(",").map(t => `<span class="badge badge-other">${escapeHtml(t.trim())}</span>`).join("") : ""}
                <button class="copy-btn" onclick="copyUrl('${escapeHtml(r.url)}')">复制链接</button>
            </div>
            <div class="resource-url">${escapeHtml(r.url)}</div>
            ${r.source ? `<div class="resource-source">来源: ${escapeHtml(r.source)}</div>` : ""}
        </div>
    `).join("");

    // Pagination
    const totalPages = Math.ceil(data.total / PAGE_SIZE);
    if (totalPages <= 1) {
        paginationEl.innerHTML = "";
        return;
    }
    paginationEl.innerHTML = `
        <button ${currentPage <= 1 ? "disabled" : ""} onclick="doSearch(${currentPage - 1})">上一页</button>
        <span>第 ${currentPage} / ${totalPages} 页</span>
        <button ${currentPage >= totalPages ? "disabled" : ""} onclick="doSearch(${currentPage + 1})">下一页</button>
    `;
}

// === Homepage ===
async function renderHome() {
    resultsEl.innerHTML = '<div class="loading">加载中...</div>';
    statsEl.textContent = "";
    paginationEl.innerHTML = "";

    try {
        const resp = await fetch(`${API_BASE}/api/stats`);
        const data = await resp.json();

        let typeSummary = Object.entries(data.by_type || {})
            .map(([k, v]) => `${typeLabel(k)} ${v}个`)
            .join(" · ");

        statsEl.textContent = `共收录 ${data.total} 个资源 · ${typeSummary}`;

        // Load recent resources
        const searchResp = await fetch(`${API_BASE}/api/search?page=1&page_size=10`);
        const searchData = await searchResp.json();
        renderResults(searchData);
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">🔍</div>
            <p>输入关键词搜索资源</p>
            <p style="margin-top:8px;font-size:13px;color:#94a3b8">支持网盘链接和实用网站检索</p>
        </div>`;
    }
}

// === Utils ===
function typeLabel(t) {
    const map = { netdisk: "网盘", website: "网址", other: "其他" };
    return map[t] || t;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function copyUrl(url) {
    try {
        await navigator.clipboard.writeText(url);
    } catch {
        // fallback
        const ta = document.createElement("textarea");
        ta.value = url;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
    }
}

// === Init ===
renderHome();
