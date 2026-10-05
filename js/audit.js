import { escapeHtml, formatDateEs, loadItinerary } from "./shared.js";

const SEV_ORDER = ["critical", "high", "medium", "low"];
const SEV_LABEL = {
  critical: "Crítico",
  high: "Alto",
  medium: "Medio",
  low: "Bajo",
};

async function loadAudit() {
  try {
    const res = await fetch("./data/audit.json", { cache: "no-store" });
    if (res.ok) return res.json();
  } catch {
    /* fall through */
  }
  // Fallback: rebuild from itinerary flags
  const data = await loadItinerary("./data/itinerary.json");
  const by = { critical: [], high: [], medium: [], low: [] };
  for (const d of data.days || []) {
    for (const f of d.dayFlags || []) {
      by[f.severity || "medium"]?.push({
        date: d.date,
        dayTitle: d.title,
        eventId: null,
        eventTitle: null,
        ...f,
      });
    }
    for (const ev of d.events || []) {
      for (const f of ev.flags || []) {
        by[f.severity || "medium"]?.push({
          date: d.date,
          dayTitle: d.title,
          eventId: ev.id,
          eventTitle: ev.title,
          ...f,
        });
      }
    }
  }
  return {
    counts: Object.fromEntries(SEV_ORDER.map((k) => [k, by[k].length])),
    flags: by,
  };
}

function render() {
  return loadAudit().then((audit) => {
    const counts = audit.counts || {};
    const countsEl = document.getElementById("audit-counts");
    countsEl.innerHTML = SEV_ORDER.map(
      (sev) =>
        `<div class="audit-count flag-${sev}"><div class="label">${SEV_LABEL[sev]}</div><div class="value">${counts[sev] ?? 0}</div></div>`
    ).join("");

    const lede = document.getElementById("audit-lede");
    const total = SEV_ORDER.reduce((s, k) => s + (counts[k] || 0), 0);
    lede.textContent = `${total} hallazgos · lo crítico exige acción del grupo (reservas / sueño / capacidad).`;

    const sections = document.getElementById("audit-sections");
    sections.innerHTML = SEV_ORDER.map((sev) => {
      const items = audit.flags?.[sev] || [];
      if (!items.length) {
        return `<section class="audit-block"><h2><span class="badge flag flag-${sev}">${SEV_LABEL[sev]}</span> Sin ítems</h2></section>`;
      }
      const rows = items
        .map((item) => {
          const href = item.date ? `./dias/${item.date}.html` : "#";
          const where = item.eventTitle
            ? escapeHtml(item.eventTitle)
            : "Día (nota general)";
          return `<li>
            <a href="${href}">
              <span class="date">${formatDateEs(item.date)}</span>
              <div>
                <h3><code>${escapeHtml(item.code)}</code> · ${where}</h3>
                <p>${escapeHtml(item.message)}</p>
              </div>
            </a>
          </li>`;
        })
        .join("");
      return `<section class="audit-block">
        <h2><span class="badge flag flag-${sev}">${SEV_LABEL[sev]}</span> ${items.length}</h2>
        <ol class="day-list audit-list">${rows}</ol>
      </section>`;
    }).join("");
  });
}

render().catch((err) => {
  console.error(err);
  document.getElementById("audit-sections").innerHTML =
    `<p style="color:var(--need)">Error cargando auditoría: ${escapeHtml(err.message)}</p>`;
});
