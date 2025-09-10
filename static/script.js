const pairsRoot = document.getElementById("pairs");
const detailsRoot = document.getElementById("details");
const refreshBtn = document.getElementById("refresh");
const shareTopBtn = document.getElementById("share-top");
const shareTopSlot = document.getElementById("share-row-top");

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

function renderShareRow(payload) {
  const row = document.createElement("div");
  row.className = "share-row";
  row.innerHTML = `
    <button class="share-btn" data-x="${payload.x_url}">Share to X</button>
    <button class="share-btn" data-tg="${payload.telegram_url}">Share to Telegram</button>
    <button class="share-btn" data-copy="${payload.page_url}">Copy link</button>
    <a class="share-btn" href="${payload.image_url}" download>Download image</a>
  `;
  row.addEventListener("click", async (e) => {
    const b = e.target.closest(".share-btn");
    if (!b) return;
    if (b.dataset.x) window.open(b.dataset.x, "_blank");
    if (b.dataset.tg) window.open(b.dataset.tg, "_blank");
    if (b.dataset.copy) {
      await navigator.clipboard.writeText(b.dataset.copy);
      b.textContent = "Copied!";
      setTimeout(() => b.textContent = "Copy link", 1200);
    }
  });
  return row;
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
  detailsRoot.innerHTML = `
    <div class="title">
      <div class="icon">🟠</div>
      <div>
        <div style="display:flex; gap:6px; align-items:center;">
          <strong>${d.name}</strong>
          <span class="tag">${d.symbol}</span>
        </div>
        <div class="tag">${d.score}% Trading Score</div>
      </div>
    </div>
    <div class="price">$${formatMoney(d.price)}</div>
    <div class="tag">${d.change_pct >= 0 ? "▲" : "▼"} ${d.change_pct}%</div>
    <div class="kv">
      <div class="item"><span class="k">Binance Volume (24h)</span><span class="v">$${formatMoney(d.volume_24h)}</span></div>
      <div class="item"><span class="k">Cap</span><span class="v">$${formatMoney(d.cap)}</span></div>
      <div class="item"><span class="k">Volatility</span><span class="v">${d.volatility}%</span></div>
      <div class="item"><span class="k">Trend</span><span class="v">${d.trend_pct}%</span></div>
      <div class="item"><span class="k">In Channel</span><span class="v">${d.in_channel ? "Yes" : "No"}</span></div>
      <div class="item"><span class="k">Exchange</span><span class="v">${d.exchange}</span></div>
    </div>
  `;

  // Inject share buttons for the selected pair
  const payload = await shareData("pair", symbol);
  const row = renderShareRow(payload);
  detailsRoot.appendChild(row);

  detailsRoot.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function boot() {
  // list
  const items = await fetchPairs();
  renderPairs(items);
  // default open first
  if (items[0]) openDetails(items[0].symbol);

  // share for top list
  shareTopSlot.innerHTML = "";
  const payload = await shareData("top");
  shareTopSlot.appendChild(renderShareRow(payload));
}

refreshBtn.addEventListener("click", boot);
shareTopBtn.addEventListener("click", async () => {
  // also copy link quickly on click
  const payload = await shareData("top");
  await navigator.clipboard.writeText(payload.page_url);
  shareTopBtn.textContent = "✔";
  setTimeout(() => shareTopBtn.textContent = "🔗 Share", 900);
});

boot();
