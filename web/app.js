/* Bank Analyzer – frontend (vanilla JS + Chart.js). Talks to the FastAPI backend in server.py. */
"use strict";

// ---------- Helpers ----------
const $ = (sel) => document.querySelector(sel);
const eur = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" });
const fmtEur = (n) => eur.format(n);
const fmtSigned = (n) => (n > 0 ? "+" : "") + eur.format(n);
const fmtDay = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
const fmtShort = new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
const fmtMonth = new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric" });
const fmtMonthShort = new Intl.DateTimeFormat("en-GB", { month: "short" });

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const parseDate = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
const monthKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const keyToDate = (k) => { const [y, m] = k.split("-").map(Number); return new Date(y, m - 1, 1); };
const sum = (arr, f = (x) => x) => arr.reduce((a, x) => a + f(x), 0);
const hexA = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const ICONS = {
  Groceries: '<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2.5 3.5h2.5l2.5 12h11l2-8.5H6"/>',
  Transport: '<rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M9 21l1.5-4M15 21l-1.5-4"/>',
  Rent: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  Online: '<path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 7v10l9 4 9-4V7M12 11v10"/>',
  Food: '<path d="M7 3v18M4.5 3v5a2.5 2.5 0 0 0 5 0V3"/><path d="M18 21V3c-2.5 1-4 3.5-4 7v3h4"/>',
  Subscriptions: '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
  Income: '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 20h16"/>',
  Other: '<circle cx="5.5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="18.5" cy="12" r="1.2"/>',
};
const icon = (cat) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[cat] || ICONS.Other}</svg>`;

// ---------- State ----------
const state = {
  txs: [],                 // {id, date: Date, description, amount, category}
  colors: {},              // category -> hex
  order: [],               // category display order
  months: 6,               // 0 = all
  view: "overview",
  q: "",
  type: "all",             // all | in | out
  cats: new Set(),         // empty = all
  shown: 60,
  trendCat: null,
};
const charts = {};
const PAGE = 60;

const colorOf = (cat) => state.colors[cat] || "#999999";

// ---------- Data ----------
async function loadData() {
  const [txRes, catRes] = await Promise.all([fetch("/api/transactions"), fetch("/api/categories")]);
  if (!txRes.ok || !catRes.ok) throw new Error("API not reachable");
  const txs = await txRes.json();
  const cats = await catRes.json();

  state.txs = txs.map((t) => ({ ...t, date: parseDate(t.date) }));
  state.colors = Object.fromEntries(cats.map((c) => [c.name, c.color]));
  const known = cats.map((c) => c.name);
  const extra = [...new Set(state.txs.map((t) => t.category))].filter((c) => !known.includes(c)).sort();
  state.order = [...known, ...extra];
}

function periodBounds() {
  if (!state.txs.length) return null;
  const first = state.txs[0].date;
  const last = state.txs[state.txs.length - 1].date;
  const start = state.months === 0 ? new Date(first.getFullYear(), first.getMonth(), 1)
    : new Date(last.getFullYear(), last.getMonth() - (state.months - 1), 1);
  return { start, end: last };
}

function periodTxs() {
  const b = periodBounds();
  return b ? state.txs.filter((t) => t.date >= b.start && t.date <= b.end) : [];
}

function monthKeys() {
  const b = periodBounds();
  const keys = [];
  for (let d = new Date(b.start); d <= b.end; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) keys.push(monthKey(d));
  return keys;
}

const isSpend = (t) => t.amount < 0 && t.category !== "Income";

// ---------- Chart defaults ----------
function setupChartDefaults() {
  if (!window.Chart) return;
  Chart.defaults.font.family = cssVar("--font");
  Chart.defaults.font.size = 12;
  Chart.defaults.color = cssVar("--ink-2");
  Chart.defaults.borderColor = cssVar("--line");
  Chart.defaults.maintainAspectRatio = false;
  Chart.defaults.plugins.legend.display = false;
  Object.assign(Chart.defaults.plugins.tooltip, {
    backgroundColor: cssVar("--ink"), padding: 10, cornerRadius: 8, boxPadding: 4, usePointStyle: true,
  });
}

function drawChart(id, config) {
  if (!window.Chart) return;
  charts[id]?.destroy();
  charts[id] = new Chart(document.getElementById(id), config);
}

const euroAxis = {
  beginAtZero: true,
  grid: { drawTicks: false },
  border: { display: false },
  ticks: { padding: 8, callback: (v) => eur.format(v).replace(/,00\s/, " ") },
};
const monthAxis = { grid: { display: false }, border: { display: false } };

// ---------- Rendering: shared ----------
function txRow(t) {
  const c = colorOf(t.category);
  return `<li class="tx">
    <span class="tx-icon" style="background:${hexA(c, .2)}">${icon(t.category)}</span>
    <div class="tx-main">
      <div class="tx-desc" title="${esc(t.description)}">${esc(t.description)}</div>
      <div class="tx-meta">${esc(t.category)} · ${fmtShort.format(t.date)}</div>
    </div>
    <span class="tx-amt ${t.amount > 0 ? "pos" : ""}">${fmtSigned(t.amount)}</span>
  </li>`;
}

function renderHeader() {
  const h = new Date().getHours();
  $("#greeting").textContent = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";

  const has = state.txs.length > 0;
  const balance = sum(state.txs, (t) => t.amount);
  const bal = $("#balance");
  bal.textContent = has ? fmtEur(balance) : fmtEur(0);
  $("#dataUntil").textContent = has ? `as of ${fmtShort.format(state.txs[state.txs.length - 1].date)}` : "no data";

  document.querySelectorAll("#periodPicker button").forEach((b) =>
    b.setAttribute("aria-checked", String(Number(b.dataset.months) === state.months)));

  const b = periodBounds();
  $("#periodRange").textContent = b
    ? (monthKey(b.start) === monthKey(b.end) ? fmtMonth.format(b.start) : `${fmtMonth.format(b.start)} – ${fmtMonth.format(b.end)}`)
    : "—";
}

// ---------- Overview ----------
function renderOverview() {
  const txs = periodTxs();
  const keys = monthKeys();
  const income = sum(txs.filter((t) => t.amount > 0), (t) => t.amount);
  const spent = -sum(txs.filter((t) => t.amount < 0), (t) => t.amount);
  const net = income - spent;
  const nMonths = Math.max(keys.length, 1);

  $("#kpiIncome").textContent = fmtEur(income);
  $("#kpiIncomeSub").textContent = `${txs.filter((t) => t.amount > 0).length} incoming payments`;
  $("#kpiSpent").textContent = fmtEur(spent);
  $("#kpiSpentSub").textContent = `${txs.filter((t) => t.amount < 0).length} payments`;
  const netEl = $("#kpiNet");
  netEl.textContent = fmtSigned(net);
  netEl.className = `kpi-value ${net >= 0 ? "pos" : "neg"}`;
  $("#kpiNetSub").textContent = income > 0 ? `Savings rate ${Math.round((net / income) * 100)} %` : "";
  $("#kpiAvg").textContent = fmtEur(spent / nMonths);
  $("#kpiAvgSub").textContent = `over ${nMonths} month${nMonths > 1 ? "s" : ""}`;

  // Cashflow bars
  const inc = Object.fromEntries(keys.map((k) => [k, 0]));
  const out = Object.fromEntries(keys.map((k) => [k, 0]));
  for (const t of txs) (t.amount > 0 ? inc : out)[monthKey(t.date)] += Math.abs(t.amount);
  drawChart("cashflowChart", {
    type: "bar",
    data: {
      labels: keys.map((k) => fmtMonthShort.format(keyToDate(k))),
      datasets: [
        { label: "Income", data: keys.map((k) => inc[k]), backgroundColor: cssVar("--pos"), borderRadius: 6, maxBarThickness: 28 },
        { label: "Spending", data: keys.map((k) => out[k]), backgroundColor: cssVar("--brand"), borderRadius: 6, maxBarThickness: 28 },
      ],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: { x: monthAxis, y: euroAxis },
      plugins: { tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmtEur(c.parsed.y)}` } } },
    },
  });

  // Donut by category
  const byCat = {};
  for (const t of txs.filter(isSpend)) byCat[t.category] = (byCat[t.category] || 0) - t.amount;
  const cats = Object.keys(byCat).sort((a, b) => byCat[b] - byCat[a]);
  const total = sum(cats, (c) => byCat[c]);
  $("#donutTotal").textContent = fmtEur(total);
  drawChart("donutChart", {
    type: "doughnut",
    data: {
      labels: cats,
      datasets: [{ data: cats.map((c) => byCat[c]), backgroundColor: cats.map(colorOf), borderColor: "#fff", borderWidth: 2, hoverOffset: 4 }],
    },
    options: {
      cutout: "72%",
      plugins: { tooltip: { callbacks: { label: (c) => ` ${c.label}: ${fmtEur(c.parsed)}` } } },
      onClick: (_, els) => els.length && openCategory(cats[els[0].index]),
    },
  });
  $("#catList").innerHTML = cats.length ? cats.map((c) => `<li><button type="button" data-cat="${esc(c)}">
      <i style="background:${colorOf(c)}"></i><span>${esc(c)}</span>
      <span class="share">${Math.round((byCat[c] / total) * 100)} %</span>
      <span class="amt">${fmtEur(byCat[c])}</span></button></li>`).join("")
    : '<li class="muted">No spending in this period.</li>';

  // Recent
  const recent = [...txs].sort((a, b) => b.date - a.date || b.id - a.id).slice(0, 8);
  $("#recentList").innerHTML = recent.length ? recent.map(txRow).join("") : '<li class="muted">No transactions in this period.</li>';
}

function openCategory(cat) {
  state.cats = new Set([cat]);
  state.type = "all";
  location.hash = "#transactions";
}

// ---------- Transactions ----------
function filteredTxs() {
  const q = state.q.trim().toUpperCase();
  return periodTxs()
    .filter((t) => (state.type === "all" || (state.type === "in" ? t.amount > 0 : t.amount < 0))
      && (state.cats.size === 0 || state.cats.has(t.category))
      && (!q || t.description.toUpperCase().includes(q)))
    .sort((a, b) => b.date - a.date || b.id - a.id);
}

function renderChips() {
  const present = new Set(periodTxs().map((t) => t.category));
  const cats = state.order.filter((c) => present.has(c) || state.cats.has(c));
  $("#catChips").innerHTML =
    `<button type="button" class="chip" data-cat="" aria-pressed="${state.cats.size === 0}">All categories</button>` +
    cats.map((c) => `<button type="button" class="chip" data-cat="${esc(c)}" aria-pressed="${state.cats.has(c)}">
      <i style="background:${colorOf(c)}"></i>${esc(c)}</button>`).join("");
  document.querySelectorAll("#typeFilter button").forEach((b) =>
    b.setAttribute("aria-checked", String(b.dataset.type === state.type)));
}

function renderTransactions() {
  renderChips();
  const txs = filteredTxs();
  const inSum = sum(txs.filter((t) => t.amount > 0), (t) => t.amount);
  const outSum = sum(txs.filter((t) => t.amount < 0), (t) => t.amount);
  $("#txSummary").innerHTML = `<span><strong>${txs.length}</strong> transactions</span>
    <span>In <strong class="pos">${fmtSigned(inSum)}</strong></span>
    <span>Out <strong>${fmtSigned(outSum)}</strong></span>`;

  const visible = txs.slice(0, state.shown);
  const groups = new Map();
  for (const t of visible) {
    const k = t.date.getTime();
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(t);
  }
  $("#txGroups").innerHTML = visible.length
    ? [...groups.values()].map((g) => `<section class="day-group">
        <div class="day-head"><span>${fmtDay.format(g[0].date)}</span><span>${fmtSigned(sum(g, (t) => t.amount))}</span></div>
        <ul class="tx-list">${g.map(txRow).join("")}</ul></section>`).join("")
    : '<p class="muted">No transactions match your filters.</p>';

  const more = $("#moreBtn");
  more.hidden = txs.length <= state.shown;
  more.textContent = `Load more (${txs.length - state.shown} remaining)`;
}

function exportCsv() {
  const txs = filteredTxs();
  const lines = ["Buchungstag;Verwendungszweck;Betrag;Kategorie"];
  for (const t of txs) {
    const amount = t.amount.toFixed(2).replace(".", ",");
    lines.push([fmtShort.format(t.date), `"${t.description.replace(/"/g, '""')}"`, amount, t.category].join(";"));
  }
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "transactions.csv" });
  a.click();
  URL.revokeObjectURL(a.href);
  toast(`Exported ${txs.length} transactions`);
}

// ---------- Analysis ----------
const NOISE = new Set(["SAGT", "DANKE", "DIENSTL.", "GMBH", "AG", "AB", "SE", "KG", "EU", "S.A", "S.A.", "R.L.", "SARL", "EUROPE"]);
function merchantName(desc) {
  const words = desc.split(/\s+/).filter((w) => w && !NOISE.has(w) && !/\d/.test(w)).slice(0, 2);
  if (!words.length) return desc;
  return words.map((w) => (w.length > 3 ? w[0] + w.slice(1).toLowerCase() : w)).join(" ");
}

function renderAnalysis() {
  const txs = periodTxs();
  const keys = monthKeys();
  const spendTx = txs.filter(isSpend);

  // Stacked bars
  const cats = state.order.filter((c) => c !== "Income" && spendTx.some((t) => t.category === c));
  const grid = Object.fromEntries(cats.map((c) => [c, Object.fromEntries(keys.map((k) => [k, 0]))]));
  for (const t of spendTx) grid[t.category][monthKey(t.date)] -= t.amount;
  $("#stackLegend").innerHTML = cats.map((c) => `<span><i style="background:${colorOf(c)}"></i>${esc(c)}</span>`).join("");
  drawChart("stackChart", {
    type: "bar",
    data: {
      labels: keys.map((k) => fmtMonth.format(keyToDate(k))),
      datasets: cats.map((c) => ({
        label: c, data: keys.map((k) => grid[c][k]), backgroundColor: colorOf(c),
        borderColor: "#fff", borderWidth: { top: 2 }, borderSkipped: false, maxBarThickness: 56,
      })),
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: { x: { ...monthAxis, stacked: true }, y: { ...euroAxis, stacked: true } },
      plugins: {
        tooltip: {
          itemSort: (a, b) => b.parsed.y - a.parsed.y,
          filter: (c) => c.parsed.y > 0,
          callbacks: {
            label: (c) => ` ${c.dataset.label}: ${fmtEur(c.parsed.y)}`,
            footer: (items) => `Total: ${fmtEur(sum(items, (i) => i.parsed.y))}`,
          },
        },
      },
    },
  });

  // Trend
  const present = state.order.filter((c) => txs.some((t) => t.category === c));
  if (!present.includes(state.trendCat)) state.trendCat = present.find((c) => c !== "Income") || present[0] || null;
  $("#trendCat").innerHTML = present.map((c) => `<option ${c === state.trendCat ? "selected" : ""}>${esc(c)}</option>`).join("");
  const per = Object.fromEntries(keys.map((k) => [k, 0]));
  for (const t of txs.filter((t) => t.category === state.trendCat)) per[monthKey(t.date)] += t.amount;
  // Yellow (Income) is too light for a line on white: use the positive green instead.
  const lineColor = state.trendCat === "Income" ? cssVar("--pos") : colorOf(state.trendCat);
  drawChart("trendChart", {
    type: "line",
    data: {
      labels: keys.map((k) => fmtMonthShort.format(keyToDate(k))),
      datasets: [{
        label: state.trendCat, data: keys.map((k) => Math.abs(per[k])),
        borderColor: lineColor, backgroundColor: hexA(lineColor.startsWith("#") ? lineColor : "#0f8a4f", .12),
        fill: true, tension: .3, pointRadius: 4, pointHoverRadius: 6, pointBackgroundColor: "#fff", borderWidth: 2.5,
      }],
    },
    options: {
      interaction: { mode: "index", intersect: false },
      scales: { x: monthAxis, y: euroAxis },
      plugins: { tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmtEur(c.parsed.y)}` } } },
    },
  });

  // Top merchants
  const m = new Map();
  for (const t of spendTx) {
    const name = merchantName(t.description);
    const e = m.get(name) || { name, total: 0, count: 0, cat: t.category };
    e.total -= t.amount; e.count += 1;
    m.set(name, e);
  }
  const top = [...m.values()].sort((a, b) => b.total - a.total).slice(0, 8);
  const max = top[0]?.total || 1;
  $("#merchants").innerHTML = top.length ? top.map((e) => `<li>
      <span class="name">${esc(e.name)}<span class="count">${e.count}×</span></span>
      <span class="amt">${fmtEur(e.total)}</span>
      <span class="bar"><span style="width:${(e.total / max) * 100}%;background:${colorOf(e.cat)}"></span></span></li>`).join("")
    : '<li class="muted">No spending in this period.</li>';
}

// ---------- Routing ----------
function render() {
  renderHeader();
  const empty = state.txs.length === 0;
  $("#emptyState").hidden = !empty;
  for (const v of ["overview", "transactions", "analysis"]) $(`#view-${v}`).hidden = empty || v !== state.view;
  document.querySelectorAll(".tabs a").forEach((a) => {
    if (a.dataset.view === state.view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if (empty) return;
  if (state.view === "overview") renderOverview();
  if (state.view === "transactions") renderTransactions();
  if (state.view === "analysis") renderAnalysis();
}

function onRoute() {
  const v = location.hash.slice(1);
  state.view = ["overview", "transactions", "analysis"].includes(v) ? v : "overview";
  state.shown = PAGE;
  render();
  window.scrollTo({ top: 0 });
}

// ---------- Toast ----------
let toastTimer;
function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// ---------- Import dialog ----------
function setupImport() {
  const dialog = $("#importDialog");
  const input = $("#fileInput");
  const zone = $("#dropzone");
  const submit = $("#importSubmit");
  const msg = $("#importMsg");
  let file = null;

  const pick = (f) => {
    file = f || null;
    $("#dropText").textContent = file ? file.name : "Drop a CSV here or click to choose";
    submit.disabled = !file;
    msg.textContent = ""; msg.className = "form-msg";
  };
  const open = () => { pick(null); input.value = ""; dialog.showModal(); };

  $("#importBtn").addEventListener("click", open);
  document.querySelectorAll("[data-open-import]").forEach((b) => b.addEventListener("click", open));
  input.addEventListener("change", () => pick(input.files[0]));
  ["dragenter", "dragover"].forEach((e) => zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((e) => zone.addEventListener(e, (ev) => { ev.preventDefault(); zone.classList.remove("drag"); }));
  zone.addEventListener("drop", (ev) => pick(ev.dataTransfer.files[0]));

  submit.addEventListener("click", async () => {
    if (!file) return;
    submit.disabled = true;
    msg.className = "form-msg"; msg.textContent = "Importing…";
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/import", { method: "POST", body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Import failed (${res.status})`);
      await loadData();
      render();
      dialog.close();
      toast(`${data.new} new of ${data.rows} transactions imported from ${data.filename}`);
    } catch (err) {
      msg.className = "form-msg error";
      msg.textContent = err.message;
      submit.disabled = false;
    }
  });
}

// ---------- Events ----------
function setupEvents() {
  window.addEventListener("hashchange", onRoute);

  $("#periodPicker").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    state.months = Number(b.dataset.months);
    state.shown = PAGE;
    render();
  });

  $("#catList").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-cat]");
    if (b) openCategory(b.dataset.cat);
  });

  let searchTimer;
  $("#search").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.q = e.target.value; state.shown = PAGE; renderTransactions(); }, 150);
  });

  $("#typeFilter").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    state.type = b.dataset.type; state.shown = PAGE;
    renderTransactions();
  });

  $("#catChips").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const c = b.dataset.cat;
    if (!c) state.cats.clear();
    else if (state.cats.has(c)) state.cats.delete(c);
    else state.cats.add(c);
    state.shown = PAGE;
    renderTransactions();
  });

  $("#moreBtn").addEventListener("click", () => { state.shown += PAGE; renderTransactions(); });
  $("#exportBtn").addEventListener("click", exportCsv);
  $("#trendCat").addEventListener("change", (e) => { state.trendCat = e.target.value; renderAnalysis(); });
}

// ---------- Boot ----------
(async function init() {
  setupChartDefaults();
  setupEvents();
  setupImport();
  try {
    await loadData();
  } catch (err) {
    toast("Could not reach the server. Is `uvicorn server:app` running?");
  }
  onRoute();
})();
