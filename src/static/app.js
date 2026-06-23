const flightInput = document.querySelector("#flight");
const searchButton = document.querySelector("#search");
const statusEl = document.querySelector("#status");
const contextEl = document.querySelector("#context");
const threatsEl = document.querySelector("#threats");

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

searchButton.addEventListener("click", loadBriefing);
flightInput.addEventListener("keydown", event => {
  if (event.key === "Enter") loadBriefing();
});
loadBriefing();
