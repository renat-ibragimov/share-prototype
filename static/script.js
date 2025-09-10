const pairsRoot = document.getElementById("pairs");
const detailsRoot = document.getElementById("details");
const refreshBtn = document.getElementById("refresh");
const shareTopBtn = document.getElementById("share-top");
const menuTop = document.getElementById("menu-top");

function closeAllMenus() {
  document.querySelectorAll(".menu").forEach(m => m.classList.add("hidden"));
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".menu-anchor")) closeAllMenus();
});

async function fetchPairs() {
  const res = await fetch("/api/pairs");
  const data = await res.json();
  return data.items || [];
}

async function fetchDetails(symbol) {
  const res = await fetch(`/api/pair/${symbol}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

async function shareData(kind, symbol=null) {
  const url = kind === "top" ? "/api/share/top" : `/api/share/pair/${symbol}`;
  const res = await fetch(url);
  return res.json();
}

function renderShareMenu(container, payload) {
  container.innerHTML = `
    <button data-x="${payload.x_url}">Share to X</button>
    <button data-tg="${payload.telegram_url}">Share to Telegram</button>
    <button data-copy="${payload.page_url}">Copy link</button>
    <a href="${payload.image_url}" download>Download image</a>
  `;
  container.onclick = async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    if (btn.dataset.x) window.open(btn.dataset.x, "_blank");
    if (btn.dataset.tg) window.open(btn.dataset.tg, "_blank");
    if (btn.dataset.copy) {
      await navigator.clipboard.writeText(btn.dataset.copy);
      btn.textContent = "Copied!";
      setTimeout(() => (btn.textContent = "Copy link"), 1200);
    }
  };
}

function renderPairs(items) {
  pairsRoot.innerHTML = "";
  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div class="rank">${item.rank}</div>
      <div class="icon">◎</div>
      <div class="grow">
        <div class="symbol">${item.symbol}</div>
        <div class="name">${item.name}</div>
      </div>
      <div class="badges">
        <span class="badge score">${item.score}% Score</span>
        <span class="badge apy">${item.apy}% APY</span>
      </div>
    `;
    row.addEventListener("click", () => openDetails(item.symbol));
    pairsRoot.appendChild(row);
  });
}

function formatMoney(n) {
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

async function openDetails(symbol) {
  const d = await fetchDetails(symbol);
  detailsRoot.classList.remove("hidden");

  // header with its own share button + menu
  detailsRoot.innerHTML = `
    <div class="card-header">
      <span class="icon">🟠</span>
      <span>${d.name} <span class="tag">${d.symbol}</span></span>
      <div class="menu-anchor" style="margin-left:auto;">
        <button class="icon-btn" id="share-coin-btn">🔗 Share</button>
        <div class="menu hidden" id="menu-coin"></div>
      </div>
    </div>
    <div class="tag">${d.score}% Trading Score</div>
    <div class="price" style="margin-top:8px;">$${formatMoney(d.price)}</div>
    <div class="tag">${d.change_pct >= 0 ? "▲" : "▼"} ${d.change_pct}%</div>
    <div class="kv" style="margin-top:8px;">
      <div class="item"><span class="k">Binance Volume (24h)</span><span class="v">$${formatMoney(d.volume_24h)}</span></div>
      <div class="item"><span class="k">Cap</span><span class="v">$${formatMoney(d.cap)}</span></div>
      <div class="item"><span class="k">Volatility</span><span class="v">${d.volatility}%</span></div>
      <div class="item"><span class="k">Trend</span><span class="v">${d.trend_pct}%</span></div>
      <div class="item"><span class="k">In Channel</span><span class="v">${d.in_channel ? "Yes" : "No"}</span></div>
      <div class="item"><span class="k">Exchange</span><span class="v">${d.exchange}</span></div>
    </div>
  `;

  const payload = await shareData("pair", symbol);
  const menuCoin = document.getElementById("menu-coin");
  renderShareMenu(menuCoin, payload);

  document.getElementById("share-coin-btn").onclick = (e) => {
    e.stopPropagation();
    menuCoin.classList.toggle("hidden");
  };

  detailsRoot.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function boot() {
  const items = await fetchPairs();
  renderPairs(items);
  if (items[0]) openDetails(items[0].symbol);

  // top share menu
  const payload = await shareData("top");
  renderShareMenu(menuTop, payload);
}

refreshBtn.addEventListener("click", boot);
shareTopBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  menuTop.classList.toggle("hidden");
});

boot();
