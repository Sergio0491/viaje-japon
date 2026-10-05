/* Shared helpers for index and day pages */

export const BOOKING_LABELS = {
  ready: "Listo",
  needs_reservation: "Hay que reservar",
  needs_ticket: "Falta comprar entrada",
  walk_in: "Sin reserva",
  na: "N/A",
};

export function formatMoney(amount, currency) {
  if (amount == null || Number.isNaN(Number(amount))) return "—";
  const n = Number(amount);
  if (currency === "JPY") {
    return `¥${Math.round(n).toLocaleString("es-CO")}`;
  }
  if (currency === "COP") {
    return `$${Math.round(n).toLocaleString("es-CO")} COP`;
  }
  if (currency === "USD") {
    return `US$${n.toLocaleString("es-CO", { maximumFractionDigits: 2 })}`;
  }
  return `${n} ${currency || ""}`.trim();
}

export function formatDateEs(iso) {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function timeLabel(hhmm) {
  return hhmm || "—";
}

export async function loadItinerary(relativePath) {
  const res = await fetch(relativePath);
  if (!res.ok) throw new Error(`No pude cargar ${relativePath}`);
  return res.json();
}

export function participantChips(participants) {
  return (participants || [])
    .map((p) => {
      const cls = p.going ? "going" : "missing";
      const tip = !p.going && p.reason ? ` title="${escapeAttr(p.reason)}"` : "";
      const reason = !p.going && p.reason ? ` · ${escapeHtml(p.reason)}` : "";
      return `<span class="chip ${cls}"${tip}>${escapeHtml(p.name.split(" ")[0])}${reason}</span>`;
    })
    .join("");
}

export function filteredDayTotals(day, events, personIds, fxJpyToCop = 21) {
  if (!personIds?.length) {
    return {
      jpy: Number(day.perPersonTotalJPY) || 0,
      cop: Number(day.perPersonTotalCOP) || 0,
    };
  }

  const hasLocalDayActivity = (events || []).some(
    (event) => !["vuelo", "hotel"].includes(event.category)
  );
  let jpy = hasLocalDayActivity ? Number(day.foodBudgetJPY) || 0 : 0;
  let directCop = 0;
  for (const event of events || []) {
    for (const cost of event.costs || []) {
      if (!cost.perPerson) continue;
      if (cost.currency === "JPY") jpy += Number(cost.amount) || 0;
      if (cost.currency === "COP") directCop += Number(cost.amount) || 0;
    }
  }
  return {
    jpy,
    cop: Math.round(jpy * fxJpyToCop + directCop),
  };
}

export function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function escapeAttr(s) {
  return escapeHtml(s).replaceAll("'", "&#39;");
}

export function bookingBadge(status) {
  const label = BOOKING_LABELS[status] || status || "N/A";
  return `<span class="badge ${status || "na"}">${label}</span>`;
}

/** Selected traveler ids from `?p=sergio,arley`. Empty = show everyone. */
export function readPersonFilter(search = window.location.search) {
  const raw = new URLSearchParams(search).get("p");
  if (!raw || !raw.trim()) return [];
  return raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

export function personFilterQuery(ids) {
  if (!ids?.length) return "";
  return `?p=${ids.map(encodeURIComponent).join(",")}`;
}

export function writePersonFilter(ids) {
  const url = new URL(window.location.href);
  if (!ids?.length) url.searchParams.delete("p");
  else url.searchParams.set("p", ids.join(","));
  history.replaceState(null, "", url.pathname + url.search + url.hash);
}

export function eventMatchesFilter(event, personIds) {
  if (!personIds?.length) return true;
  return (event.participants || []).some(
    (p) => p.going && personIds.includes(String(p.id).toLowerCase())
  );
}

export function dayMatchesFilter(day, personIds) {
  if (!personIds?.length) return true;
  return (day.events || []).some((e) => eventMatchesFilter(e, personIds));
}

export function filteredEvents(day, personIds) {
  if (!personIds?.length) return day.events || [];
  return (day.events || []).filter((e) => eventMatchesFilter(e, personIds));
}

export function shortName(traveler) {
  return traveler.short || traveler.name.split(" ")[0];
}

