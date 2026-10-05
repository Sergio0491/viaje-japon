import {
  formatDateEs,
  formatMoney,
  loadItinerary,
  readPersonFilter,
  writePersonFilter,
  personFilterQuery,
  dayMatchesFilter,
  filteredEvents,
  shortName,
  escapeHtml,
} from "./shared.js";

let state = {
  travelers: [],
  days: [],
  selected: [],
};

function renderFilters() {
  const el = document.getElementById("travelers");
  if (!el) return;

  const allActive = state.selected.length === 0;
  el.innerHTML = `
    <li>
      <button type="button" class="filter-chip ${allActive ? "is-active" : ""}" data-filter="all" aria-pressed="${allActive}">
        Todos
      </button>
    </li>
    ${state.travelers
      .map((t) => {
        const on = state.selected.includes(t.id);
        return `<li>
          <button type="button" class="filter-chip ${on ? "is-active" : ""}" data-filter="${escapeHtml(t.id)}" aria-pressed="${on}">
            ${escapeHtml(shortName(t))}
          </button>
        </li>`;
      })
      .join("")}
  `;

  el.querySelectorAll("button.filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.filter;
      if (id === "all") {
        state.selected = [];
      } else if (state.selected.includes(id)) {
        state.selected = state.selected.filter((x) => x !== id);
      } else {
        state.selected = [...state.selected, id];
      }
      writePersonFilter(state.selected);
      renderFilters();
      renderDays();
      renderFilterStatus();
    });
  });
}

function renderFilterStatus() {
  const status = document.getElementById("filter-status");
  if (!status) return;
  if (!state.selected.length) {
    status.textContent = "Mostrando el itinerario completo del grupo.";
    return;
  }
  const names = state.selected.map((id) => {
    const t = state.travelers.find((x) => x.id === id);
    return t ? shortName(t) : id;
  });
  const n = state.days.filter((d) => dayMatchesFilter(d, state.selected)).length;
  status.textContent = `Filtro: ${names.join(", ")} · ${n} día${n === 1 ? "" : "s"} con eventos.`;
}

function renderDays() {
  const listEl = document.getElementById("day-list");
  if (!listEl) return;

  const q = personFilterQuery(state.selected);
  const visible = state.days.filter((d) => dayMatchesFilter(d, state.selected));

  if (!visible.length) {
    listEl.innerHTML =
      '<li style="padding:1.25rem 0;color:var(--muted);">Ningún día coincide con ese filtro.</li>';
    return;
  }

  listEl.innerHTML = visible
    .map((day) => {
      const dayIndex = state.days.findIndex((item) => item.date === day.date);
      const events = filteredEvents(day, state.selected);
      const href = `./dias/${day.date}.html${q}`;
      const total =
        day.perPersonTotalJPY > 0
          ? `${formatMoney(day.perPersonTotalJPY, "JPY")} / pers.`
          : "—";
      const countLabel = state.selected.length
        ? `${events.length} evento${events.length === 1 ? "" : "s"}`
        : "";
      const flags = [
        ...(day.dayFlags || []),
        ...events.flatMap((e) => e.flags || []),
      ];
      const hasCritical = flags.some((f) => f.severity === "critical");
      const hasHigh = flags.some((f) => f.severity === "high");
      const flagChip = hasCritical
        ? '<span class="badge flag flag-critical">alerta</span>'
        : hasHigh
          ? '<span class="badge flag flag-high">revisar</span>'
          : "";
      return `<li class="day-stop">
        <a href="${href}">
          <span class="route-marker" aria-hidden="true"><b>${String(dayIndex).padStart(2, "0")}</b></span>
          <div class="day-copy">
            <div class="day-kicker">
              <span class="date">${formatDateEs(day.date)}</span>
              <span class="city">${escapeHtml(day.city || "")}</span>
            </div>
            <h2>Día ${dayIndex}: ${escapeHtml(day.city || "En ruta")} ${flagChip}</h2>
            <p>${escapeHtml(day.summary || day.city || "")}${
              countLabel
                ? ` · <span class="day-match-count">${countLabel}</span>`
                : ""
            }</p>
          </div>
          <span class="total">${total}</span>
        </a>
      </li>`;
    })
    .join("");
}

async function main() {
  const data = await loadItinerary("./data/itinerary.json");
  const meta = data.meta;
  state.travelers = meta.travelers || [];
  state.days = data.days || [];
  state.selected = readPersonFilter().filter((id) =>
    state.travelers.some((t) => t.id === id)
  );

  const ledeEl = document.getElementById("lede");
  if (ledeEl) {
    ledeEl.textContent = `${formatDateEs(meta.startDate)} — ${formatDateEs(meta.endDate)} · Tokio, Fuji, Kansai y Kanazawa`;
  }

  const countdown = document.getElementById("trip-countdown");
  const countdownLabel = document.getElementById("trip-countdown-label");
  if (countdown && countdownLabel) {
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const start = new Date(`${meta.startDate}T12:00:00`);
    const end = new Date(`${meta.endDate}T12:00:00`);
    const daysUntil = Math.ceil((start - today) / 86400000);
    if (daysUntil > 0) {
      countdown.textContent = `${daysUntil} día${daysUntil === 1 ? "" : "s"}`;
      countdownLabel.textContent = "para empezar la ruta";
    } else if (today <= end) {
      const currentDay = Math.floor((today - start) / 86400000) + 1;
      countdown.textContent = `Día ${currentDay} de 21`;
      countdownLabel.textContent = "estamos en Japón";
    } else {
      countdown.textContent = "21 días";
      countdownLabel.textContent = "de recuerdos en Japón";
    }
  }

  renderFilters();
  renderFilterStatus();
  renderDays();
}

main().catch((err) => {
  console.error(err);
  const listEl = document.getElementById("day-list");
  if (listEl) {
    listEl.innerHTML = `<li style="padding:1rem 0;color:#a33b1a;">Error cargando itinerario: ${err.message}. Abrí el sitio con un servidor local (ver README).</li>`;
  }
});
