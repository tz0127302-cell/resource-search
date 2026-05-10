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
const filterBar = document.getElementById("filterBar");

// Category color map
const CATEGORY_COLORS = {
    "办公": { bg: "#eef2ff", icon: "📄" },
    "设计": { bg: "#fdf2f8", icon: "🎨" },
    "开发": { bg: "#ecfdf5", icon: "💻" },
    "系统工具": { bg: "#fefce8", icon: "🔧" },
    "媒体": { bg: "#fef2f2", icon: "🎵" },
    "网络": { bg: "#f0f9ff", icon: "🌐" },
};

function getCategoryStyle(tag) {
    const cat = CATEGORY_COLORS[tag];
    return cat || { bg: "#f3f4f6", icon: "📦" };
}

// === Event listeners ===
searchBtn.addEventListener("click", () => doSearch(1));
searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch(1);
});

filterBar.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    filterBar.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentType = btn.dataset.type || null;
    doSearch(1);
});

// === Core search ===
async function doSearch(page) {
    currentPage = page;
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
    if (currentType) params.set("resource_type", "other");
    if (q || currentType) {
        if (q) params.set("q", q);
        if (currentType) {
            params.set("q", currentType);
        }
    }
    params.set("page", page);
    params.set("page_size", PAGE_SIZE);

    try {
        const resp = await fetch(`${API_BASE}/api/search?${params}`);
        if (!resp.ok) throw new Error("请求失败");
        const data = await resp.json();
        renderResults(data);
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">😅</div>
            <p>搜索出错了：${err.message}</p>
        </div>`;
    }
}

function renderResults(data) {
    statsEl.textContent = data.total > 0
        ? `共找到 ${data.total} 款软件`
        : "";

    if (data.results.length === 0) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">🔍</div>
            <p>没找到匹配的软件</p>
            <p style="margin-top:8px;font-size:13px;color:#94a3b8">试试其他关键词</p>
        </div>`;
        paginationEl.innerHTML = "";
        return;
    }

    resultsEl.innerHTML = data.results.map((r) => {
        const tags = (r.tags || "").split(",").filter(Boolean);
        const primaryTag = tags[0] || r.resource_type;
        const catStyle = getCategoryStyle(primaryTag);

        return `
            <div class="software-card">
                <div class="software-icon" style="background: ${catStyle.bg}">
                    ${catStyle.icon}
                </div>
                <div class="software-body">
                    <h3>${escapeHtml(r.title)}</h3>
                    <p class="software-desc">${escapeHtml(r.description || "一款实用的软件，推荐给大家")}</p>
                    <div class="software-meta">
                        ${tags.map(t => `<span class="badge badge-other" style="background:${getCategoryStyle(t).bg};color:#6366f1">${escapeHtml(t.trim())}</span>`).join("")}
                        <span class="badge badge-${r.resource_type}">${typeLabel(r.resource_type)}</span>
                    </div>
                    <div class="software-url">
                        <span>🔗</span>
                        <span class="url-text">${escapeHtml(r.url)}</span>
                        <button class="btn-copy" onclick="copyUrl('${escapeHtml(r.url)}')" style="padding:2px 10px;font-size:12px">复制</button>
                    </div>
                </div>
                <div class="software-actions">
                    <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener" class="btn-download">⬇ 下载</a>
                </div>
            </div>
        `;
    }).join("");

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
        statsEl.textContent = `📦 共收录 ${data.total} 款软件 · ${typeSummary}`;

        const searchResp = await fetch(`${API_BASE}/api/search?page=1&page_size=20`);
        const searchData = await searchResp.json();
        renderResults(searchData);
    } catch (err) {
        resultsEl.innerHTML = `<div class="empty-state">
            <div class="icon">📦</div>
            <p>输入关键词搜索软件</p>
            <p style="margin-top:8px;font-size:13px;color:#94a3b8">试试搜索"办公"、"设计"等类别</p>
        </div>`;
    }
}

// === Utils ===
function typeLabel(t) {
    const map = { netdisk: "网盘下载", website: "官网", other: "其他" };
    return map[t] || t;
}

function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function copyUrl(url) {
    try {
        await navigator.clipboard.writeText(url);
        alert("链接已复制！");
    } catch {
        const ta = document.createElement("textarea");
        ta.value = url;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        alert("链接已复制！");
    }
}

// === Init ===
renderHome();
