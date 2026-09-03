import { rollingMonths, monthKey, isInRollingWindow } from "./date-utils.js";

const state = { data: null, query: "", onlineOnly: false };
const els = {
  months: document.querySelector("#month-grid"), anytime: document.querySelector("#anytime-grid"),
  anytimeSection: document.querySelector("#anytime-section"), search: document.querySelector("#search"),
  online: document.querySelector("#online-only"), freshness: document.querySelector("#freshness"),
  count: document.querySelector("#result-count"), error: document.querySelector("#load-error"),
  sourceSummary: document.querySelector("#source-summary"), sourceList: document.querySelector("#source-list")
};
const themeToggle = document.querySelector("#theme-toggle");
const dateFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" });
const monthFmt = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" });
const updatedFmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "long", year: "numeric" });

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

function syncThemeControl() {
  const dark = document.documentElement.dataset.theme === "dark";
  themeToggle.setAttribute("aria-pressed", String(dark));
  themeToggle.setAttribute("aria-label", `Switch to ${dark ? "light" : "dark"} mode`);
}

themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("cpd-theme", next);
  syncThemeControl();
});
syncThemeControl();

function matches(item) {
  const text = [item.title, item.provider, item.type, item.description, item.location, ...(item.tags || [])].join(" ").toLowerCase();
  return (!state.query || text.includes(state.query)) && (!state.onlineOnly || item.delivery?.toLowerCase() === "online");
}

function card(item) {
  const date = item.startDate ? dateFmt.format(new Date(`${item.startDate}T12:00:00`)) : "Anytime";
  const time = item.startTime ? `${item.startTime}${item.endTime ? `–${item.endTime}` : ""}` : "";
  const meta = [time, item.delivery, item.location].filter(Boolean).map(escapeHtml).join(" · ");
  const cost = item.isFree === true ? '<span class="cost free">Free</span>' : item.cost && item.cost !== "Unknown" ? `<span class="cost">${escapeHtml(item.cost)}</span>` : "";
  return `<article class="opportunity-card">
    <div class="badges"><span class="badge provider provider-${escapeHtml(item.provider.toLowerCase().replace(/[^a-z0-9]/g, ""))}">${escapeHtml(item.provider)}</span><span class="badge">${escapeHtml(item.type)}</span>${cost}</div>
    <p class="card-date">${escapeHtml(date)}</p><h3>${escapeHtml(item.title)}</h3>
    ${meta ? `<p class="meta">${meta}</p>` : ""}${item.description ? `<p class="description">${escapeHtml(item.description)}</p>` : ""}
    <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">View opportunity <span aria-hidden="true">→</span><span class="sr-only">: ${escapeHtml(item.title)} (opens in a new tab)</span></a>
  </article>`;
}

function render() {
  const visible = state.data.opportunities.filter(matches);
  const months = rollingMonths();
  els.months.innerHTML = months.map((month, index) => {
    const items = visible.filter(item => !item.isSelfPaced && item.startDate?.startsWith(monthKey(month)));
    return `<section class="month-column" aria-labelledby="month-${index}"><div class="month-title"><h3 id="month-${index}">${monthFmt.format(month)}</h3><span>${items.length || "—"}</span></div><div class="card-list">${items.length ? items.map(card).join("") : '<p class="empty">Nothing discovered yet —<br>check back soon.</p>'}</div></section>`;
  }).join("");
  const anytime = visible.filter(item => item.isSelfPaced);
  els.anytimeSection.hidden = !anytime.length;
  els.anytime.innerHTML = anytime.map(card).join("");
  const datedCount = visible.filter(item => isInRollingWindow(item.startDate)).length;
  els.count.textContent = `${datedCount} ${datedCount === 1 ? "opportunity" : "opportunities"} coming up`;
}

function renderHealth() {
  const sources = state.data.sources || [];
  const failures = sources.filter(source => source.status !== "ok").length;
  els.sourceSummary.textContent = `${sources.length} sources checked${failures ? ` · ${failures} needs attention` : ""}`;
  els.sourceList.innerHTML = sources.map(source => `<div class="source-row"><span class="health-icon ${source.status}" aria-hidden="true">${source.status === "ok" ? "✓" : "!"}</span><span><strong>${escapeHtml(source.provider)}</strong><small>${source.status === "ok" ? `${source.count} opportunities` : `Last successful: ${source.lastSuccessful ? updatedFmt.format(new Date(source.lastSuccessful)) : "not yet"}`}</small></span></div>`).join("");
}

async function init() {
  try {
    const response = await fetch("./data/opportunities.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    const updated = new Date(state.data.generatedAt);
    els.freshness.innerHTML = `<span class="status-dot" aria-hidden="true"></span>Last updated ${updatedFmt.format(updated)}`;
    renderHealth(); render();
  } catch (error) {
    console.error(error); els.error.hidden = false; els.months.hidden = true; els.freshness.textContent = "Update unavailable";
  }
}

els.search.addEventListener("input", event => { state.query = event.target.value.trim().toLowerCase(); render(); });
els.online.addEventListener("change", event => { state.onlineOnly = event.target.checked; render(); });
init();
