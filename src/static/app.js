const flightInput = document.querySelector("#flight");
const searchButton = document.querySelector("#search");
const statusEl = document.querySelector("#status");
const contextEl = document.querySelector("#context");
const threatsEl = document.querySelector("#threats");
const baseWeatherEl = document.querySelector("#baseWeather");
const settingsToggle = document.querySelector("#settingsToggle");
const settingsPanel = document.querySelector("#settingsPanel");
const settingsClose = document.querySelector("#settingsClose");
const stationForm = document.querySelector("#stationForm");
const stationInput = document.querySelector("#stationInput");
const stationSave = document.querySelector("#stationSave");
const stationEditList = document.querySelector("#stationEditList");
const themeToggle = document.querySelector("#themeToggle");
const themeLabel = document.querySelector("#themeLabel");
const eventCountEl = document.querySelector("#eventCount");

const STATIONS_KEY = "opsIntelBaseStations";
const THEME_KEY = "opsIntelTheme";
let editingStation = "";

function syncMobileTheme() {
  document.body.classList.toggle("mobileBriefing", window.innerWidth <= 820);
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function eventSimilarity(event) {
  const value = Number(event.similarity ?? event.similarity_score ?? 50);
  if (!Number.isFinite(value)) return 50;
  return Math.round(value > 1 ? value : value * 100);
}

function riskLabel(value) {
  return String(value || "LOW").toUpperCase();
}

function applyTheme(theme) {
  const normalized = theme === "light" ? "light" : "dark";
  document.body.classList.toggle("lightTheme", normalized === "light");
  document.body.classList.toggle("darkTheme", normalized === "dark");
  themeToggle.checked = normalized === "light";
  themeLabel.textContent = normalized === "light" ? "Light" : "Dark";
  localStorage.setItem(THEME_KEY, normalized);
}

function normalizeStation(value) {
  return String(value || "").trim().toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
}

function loadStations() {
  try {
    const saved = JSON.parse(localStorage.getItem(STATIONS_KEY) || "[]");
    if (Array.isArray(saved) && saved.length) return saved.map(normalizeStation).filter(Boolean);
  } catch (error) {
    localStorage.removeItem(STATIONS_KEY);
  }
  return ["RKSI"];
}

function saveStations(stations) {
  const unique = [...new Set(stations.map(normalizeStation).filter(station => station.length === 4))];
  localStorage.setItem(STATIONS_KEY, JSON.stringify(unique));
  return unique;
}

function renderStationEditor() {
  const stations = loadStations();
  stationEditList.innerHTML = stations.map(station => `
    <div class="stationEditItem">
      <b>${esc(station)}</b>
      <button type="button" data-edit-station="${esc(station)}">Edit</button>
      <button type="button" data-delete-station="${esc(station)}">Delete</button>
    </div>
  `).join("") || `<p class="emptyState">No base stations saved.</p>`;
  stationEditList.querySelectorAll("[data-edit-station]").forEach(button => {
    button.addEventListener("click", () => {
      editingStation = button.dataset.editStation;
      stationInput.value = editingStation;
      stationSave.textContent = "Save";
      stationInput.focus();
    });
  });
  stationEditList.querySelectorAll("[data-delete-station]").forEach(button => {
    button.addEventListener("click", () => {
      saveStations(loadStations().filter(station => station !== button.dataset.deleteStation));
      renderStationEditor();
      renderBaseWeather();
    });
  });
}

async function renderEventCount() {
  eventCountEl.textContent = "Loading...";
  try {
    const response = await fetch("/api/ops-intel/status");
    if (!response.ok) throw new Error("Status unavailable");
    const status = await response.json();
    eventCountEl.textContent = `${status.items_in_database ?? 0} events`;
  } catch (error) {
    eventCountEl.textContent = "Unavailable";
  }
}

function openSettings() {
  settingsPanel.classList.remove("hidden");
  document.body.classList.add("settingsOpen");
  renderStationEditor();
  renderEventCount();
  stationInput.focus();
}

function closeSettings() {
  settingsPanel.classList.add("hidden");
  document.body.classList.remove("settingsOpen");
  editingStation = "";
  stationInput.value = "";
  stationSave.textContent = "Add";
}

async function fetchStationWeather(station) {
  const response = await fetch(`/api/weather/${encodeURIComponent(station)}`);
  if (!response.ok) throw new Error("Weather unavailable");
  return response.json();
}

async function renderBaseWeather() {
  const stations = loadStations();
  if (!stations.length) {
    baseWeatherEl.innerHTML = `
      <article class="baseWxCard">
        <h2>Base Station WX</h2>
        <p class="emptyState">Open settings and add a base station.</p>
      </article>
    `;
    return;
  }
  baseWeatherEl.innerHTML = `
    <article class="baseWxCard">
      <div class="baseWxHead">
        <h2>Base Station WX</h2>
        <button type="button" id="refreshBaseWx">Refresh</button>
      </div>
      <div class="baseWxList">
        ${stations.map(station => `
          <section class="baseWxItem" data-station="${esc(station)}">
            <strong>${esc(station)}</strong>
            <span>Loading weather...</span>
          </section>
        `).join("")}
      </div>
    </article>
  `;
  document.querySelector("#refreshBaseWx").addEventListener("click", renderBaseWeather);
  await Promise.all(stations.map(async station => {
    const item = baseWeatherEl.querySelector(`[data-station="${station}"]`);
    try {
      const wx = await fetchStationWeather(station);
      item.innerHTML = `
        <strong>${esc(station)}</strong>
        <pre>${esc(wx.metar || "METAR unavailable")}</pre>
        <pre>${esc(wx.taf || "TAF unavailable")}</pre>
      `;
    } catch (error) {
      item.innerHTML = `<strong>${esc(station)}</strong><span>Weather unavailable</span>`;
    }
  }));
}

function renderContext(ctx) {
  const searchLinks = (ctx.flight_search_links || []).map(link =>
    `<a href="${esc(link.url)}" target="_blank" rel="noreferrer">${esc(link.label)}</a>`
  ).join("");
  contextEl.classList.remove("hidden");
  contextEl.innerHTML = `
    <div class="contextTop">
      <div>
        <strong>${esc(ctx.flight_number)} ${esc(ctx.route)}</strong>
        <span>${esc(ctx.departure_icao)} -> ${esc(ctx.arrival_icao)} - ${esc(ctx.aircraft)}</span>
      </div>
      <b class="risk ${esc(ctx.risk_level).toLowerCase()}">${esc(ctx.risk_level)}</b>
    </div>
    <div class="chips">
      <span>${esc(ctx.destination_runway || "RWY TBD")}</span>
      <span>${esc(ctx.weather)}</span>
    </div>
    ${(ctx.messages || []).map(m => `<p class="msg">${esc(m)}</p>`).join("")}
    ${searchLinks ? `<div class="flightSearch"><b>Google flight lookup</b>${searchLinks}</div>` : ""}
    <div class="forecastBasis">
      <b>Threat basis</b>
      <span>${esc(ctx.arrival_weather_time || "Arrival time unavailable")}</span>
      <pre class="weatherText">${esc(ctx.arrival_taf || "Arrival TAF segment unavailable")}</pre>
    </div>
    <pre class="weatherText">${esc(ctx.metar || "METAR unavailable")}</pre>
    <pre class="weatherText">${esc(ctx.taf || "TAF unavailable")}</pre>
  `;
}

function renderThreats(threats) {
  threatsEl.innerHTML = `
    <h2 class="threatsTitle">Today's Top Threats</h2>
    ${threats.map((threat, index) => `
    <section class="threat">
      <h2><span class="desktopThreatPrefix">Threat ${index + 1}: </span><span class="threatRank">${index + 1}</span>${esc(threat.title)}</h2>
      <p>${esc(threat.description)}</p>
      <div class="events">
        ${threat.events.map(event => `
          <details>
            <summary>
              <span class="dropIcon">&gt;</span>
              <span class="eventLine">${esc(event.one_line)}</span>
              <span class="mobileEventMeta">Events 1 - Similar ${eventSimilarity(event)}%</span>
              <b class="risk eventRisk ${esc(event.severity || "Low").toLowerCase()}">${esc(riskLabel(event.severity))}</b>
            </summary>
            <div class="detail">
              <h3>${esc(event.detail_title)}</h3>
              <div class="eventMeta">
                <span>${esc(event.date || "DATE TBD")}</span>
                <span>${esc(event.operation_type || "Operation TBD")}</span>
                <span>${esc(event.category || "Category TBD")}</span>
                <span>${esc(event.severity || "Severity TBD")}</span>
              </div>
              <p>${esc(event.summary)}</p>
              <b>Contributing factors</b>
              <ul>${event.contributing_factors.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
              <b>Operational lessons</b>
              <ul>${event.operational_lessons.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
              <b>A350 / B787 long-haul relevance</b>
              <p>${esc(event.a350_b787_applicability || "")}</p>
              <b>Recommended action</b>
              <p>${esc(event.recommended_action || "")}</p>
              <p class="brief">${esc(event.pilot_briefing_sentence)}</p>
            </div>
          </details>
        `).join("")}
      </div>
    </section>
  `).join("")}
  `;
}

async function loadBriefing() {
  const flight = flightInput.value.trim() || "KE629";
  statusEl.textContent = "Loading briefing...";
  searchButton.disabled = true;
  try {
    const response = await fetch(`/api/briefing/${encodeURIComponent(flight)}`);
    if (!response.ok) throw new Error("Briefing unavailable");
    const data = await response.json();
    baseWeatherEl.classList.add("hidden");
    renderContext(data.flight_context);
    renderThreats(data.top_threats || []);
    document.body.classList.add("briefingLoaded");
    statusEl.textContent = "";
  } catch (error) {
    document.body.classList.remove("briefingLoaded");
    statusEl.textContent = "Unable to load briefing. Try again.";
  } finally {
    searchButton.disabled = false;
  }
}

settingsToggle.addEventListener("click", openSettings);
settingsClose.addEventListener("click", closeSettings);
settingsPanel.addEventListener("click", event => {
  if (event.target === settingsPanel) closeSettings();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && !settingsPanel.classList.contains("hidden")) closeSettings();
});
stationForm.addEventListener("submit", event => {
  event.preventDefault();
  const station = normalizeStation(stationInput.value);
  if (station.length !== 4) return;
  const stations = loadStations().filter(item => item !== editingStation && item !== station);
  saveStations([...stations, station]);
  editingStation = "";
  stationInput.value = "";
  stationSave.textContent = "Add";
  renderStationEditor();
  renderBaseWeather();
  closeSettings();
});
searchButton.addEventListener("click", loadBriefing);
flightInput.addEventListener("keydown", event => {
  if (event.key === "Enter") loadBriefing();
});
window.addEventListener("resize", syncMobileTheme);
themeToggle.addEventListener("change", () => applyTheme(themeToggle.checked ? "light" : "dark"));
syncMobileTheme();
applyTheme(localStorage.getItem(THEME_KEY) || "dark");
renderStationEditor();
renderBaseWeather();
