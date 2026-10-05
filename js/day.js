import {
  BOOKING_LABELS,
  bookingBadge,
  formatDateEs,
  formatMoney,
  loadItinerary,
  participantChips,
  timeLabel,
  escapeHtml,
  readPersonFilter,
  personFilterQuery,
  filteredEvents,
  filteredDayTotals,
  shortName,
} from "./shared.js";

const DAY_DATE = document.body.dataset.date;
const MAP_ATTR =
  'Tiles &copy; <a href="https://www.esri.com/">Esri</a> · datos OSM/Garmin/etc.';
/** World Street Map: etiquetas en alfabeto latino (no kanji) en Japón. */
const TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";

const mapInstances = new Map();

function placeToLatLng(place) {
  if (!place) return null;
  if (typeof place.lat === "number" && typeof place.lng === "number") {
    return { lat: place.lat, lng: place.lng };
  }
  return null;
}

/** Prefer coordinates; otherwise a cleaned searchable name (never Excel blurbs). */
function placeQuery(place) {
  if (!place) return "";
  if (typeof place.lat === "number" && typeof place.lng === "number") {
    return `${place.lat},${place.lng}`;
  }
  return cleanMapsQuery(place.query || place.name || "");
}

function cleanMapsQuery(raw) {
  let q = String(raw || "");
  q = q.replace(/\([^)]*\)/g, " ");
  q = q.replace(/\bTokio v[12]\b/gi, "Tokyo");
  q = q.replace(/\bKansai\b[^(]*/gi, "Kyoto");
  q = q.replace(/\bMt\.?\s*fuji\b/gi, "Kawaguchiko");
  q = q.replace(/\bJapan\b/gi, "");
  q = q.replace(/\baca\b.+$/gi, "");
  q = q.replace(/\s+/g, " ").trim();
  // Drop rows that are not places
  const lower = q.toLowerCase();
  if (
    lower.startsWith("transporte") ||
    lower.startsWith("envio") ||
    lower.startsWith("envío") ||
    lower.startsWith("actividad libre") ||
    lower.startsWith("exploracion") ||
    lower.startsWith("exploración")
  ) {
    return "";
  }
  return q;
}

function isUsablePlace(place) {
  if (!place) return false;
  if (typeof place.lat === "number" && typeof place.lng === "number") return true;
  return Boolean(cleanMapsQuery(place.query || place.name || ""));
}

function placesAreSame(a, b) {
  if (!a || !b) return false;
  if (
    typeof a.lat === "number" &&
    typeof b.lat === "number" &&
    a.lat === b.lat &&
    a.lng === b.lng
  ) {
    return true;
  }
  const qa = cleanMapsQuery(a.query || a.name || "").toLowerCase();
  const qb = cleanMapsQuery(b.query || b.name || "").toLowerCase();
  return Boolean(qa && qa === qb);
}

function baseTileLayer() {
  return L.tileLayer(TILE_URL, {
    attribution: MAP_ATTR,
    maxZoom: 19,
  });
}

function googleMapsPlaceUrl(place) {
  if (!isUsablePlace(place)) return null;
  const q = placeQuery(place);
  if (!q) return null;
  const params = new URLSearchParams({ api: "1", query: q, hl: "es" });
  return `https://www.google.com/maps/search/?${params.toString()}`;
}

function googleMapsDirUrl(fromPlace, toPlace, mode) {
  if (mode === "flight") return null;
  if (!isUsablePlace(fromPlace) || !isUsablePlace(toPlace)) return null;
  if (placesAreSame(fromPlace, toPlace)) return null;

  const travelmode = {
    walk: "walking",
    metro: "transit",
    tren: "transit",
    bus: "transit",
    taxi: "driving",
    none: "walking",
  }[mode] || "transit";

  const origin = placeQuery(fromPlace);
  const destination = placeQuery(toPlace);
  if (!origin || !destination || origin === destination) return null;

  const params = new URLSearchParams({
    api: "1",
    origin,
    destination,
    travelmode,
    hl: "es",
  });
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

function osrmProfile(mode) {
  if (mode === "walk" || mode === "none") return "walking";
  if (mode === "taxi") return "driving";
  return null;
}

function initDayMap(day) {
  const el = document.getElementById("day-map");
  if (!el || !window.L) return;

  const center = day.mapCenter || { lat: 35.68, lng: 139.76 };
  const map = L.map(el, {
    scrollWheelZoom: false,
    dragging: false,
    tap: false,
  }).setView(
    [center.lat, center.lng],
    12
  );
  baseTileLayer().addTo(map);

  const bounds = [];
  if (day.hotel?.name && center.lat != null) {
    L.marker([center.lat, center.lng])
      .addTo(map)
      .bindPopup(day.hotel.name);
    bounds.push([center.lat, center.lng]);
  }

  for (const ev of day.events || []) {
    const to = placeToLatLng(ev.to);
    if (to) {
      L.circleMarker([to.lat, to.lng], {
        radius: 5,
        color: "#c41e3a",
        fillColor: "#c41e3a",
        fillOpacity: 0.85,
        weight: 1,
      })
        .addTo(map)
        .bindPopup(ev.title);
      bounds.push([to.lat, to.lng]);
    }
  }

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [28, 28], maxZoom: 13 });
  }

  setTimeout(() => map.invalidateSize(), 50);
}

async function fetchOsrmRoute(from, to, profile) {
  const url =
    `https://router.project-osrm.org/route/v1/${profile}/` +
    `${from.lng},${from.lat};${to.lng},${to.lat}` +
    `?overview=full&geometries=geojson`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`OSRM ${res.status}`);
  const data = await res.json();
  if (data.code !== "Ok" || !data.routes?.[0]) throw new Error("Sin ruta OSRM");
  return data.routes[0];
}

async function renderEventMap(event, container) {
  if (mapInstances.has(event.id)) {
    const existing = mapInstances.get(event.id);
    if (existing) setTimeout(() => existing.invalidateSize(), 50);
    return;
  }

  const from = placeToLatLng(event.from);
  const to = placeToLatLng(event.to);
  const mode = event.travel?.mode || "none";
  const distinctTrip =
    isUsablePlace(event.from) &&
    isUsablePlace(event.to) &&
    !placesAreSame(event.from, event.to);

  let gmapsUrl = distinctTrip
    ? googleMapsDirUrl(event.from, event.to, mode)
    : null;
  let gmapsLabel = "Abrir ruta en Google Maps";
  if (!gmapsUrl) {
    gmapsUrl = googleMapsPlaceUrl(event.to || event.from);
    gmapsLabel = "Ver lugar en Google Maps";
  }
  if (!window.L) {
    const link = gmapsUrl
      ? `<p class="map-links"><a class="map-cta" href="${gmapsUrl}" target="_blank" rel="noopener">${gmapsLabel}</a></p>`
      : "";
    container.innerHTML = `<p class="map-fallback">Mapa no disponible en este momento.</p>${link}`;
    container.classList.add("is-ready");
    return;
  }
  if (!from && !to) {
    const link = gmapsUrl
      ? `<p class="map-links"><a class="map-cta" href="${gmapsUrl}" target="_blank" rel="noopener">${gmapsLabel}</a></p>`
      : "";
    container.innerHTML =
      `<p class="map-fallback">Sin coordenadas en el mapa embebido; usá el enlace.</p>${link}`;
    container.classList.add("is-ready");
    return;
  }

  container.innerHTML = "";
  const mapEl = document.createElement("div");
  mapEl.className = "event-map-canvas";
  container.appendChild(mapEl);

  const linkWrap = document.createElement("p");
  linkWrap.className = "map-links";
  container.appendChild(linkWrap);
  linkWrap.innerHTML = gmapsUrl
    ? `<a class="map-cta" href="${gmapsUrl}" target="_blank" rel="noopener">${gmapsLabel}</a>`
    : "";

  const only = to || from;
  const map = L.map(mapEl, {
    scrollWheelZoom: false,
    dragging: false,
    tap: false,
  }).setView(
    [only.lat, only.lng],
    14
  );
  baseTileLayer().addTo(map);
  mapInstances.set(event.id, map);

  const markers = [];
  if (distinctTrip && from) {
    markers.push(
      L.marker([from.lat, from.lng])
        .addTo(map)
        .bindPopup(event.from?.name || "Origen")
    );
  }
  if (to) {
    markers.push(
      L.marker([to.lat, to.lng])
        .addTo(map)
        .bindPopup(event.to?.name || (distinctTrip ? "Destino" : "Lugar"))
    );
  } else if (from) {
    markers.push(
      L.marker([from.lat, from.lng])
        .addTo(map)
        .bindPopup(event.from?.name || "Lugar")
    );
  }

  if (distinctTrip && from && to) {
    const profile = osrmProfile(mode);
    if (profile) {
      try {
        const route = await fetchOsrmRoute(from, to, profile);
        const coords = route.geometry.coordinates.map(([lng, lat]) => [
          lat,
          lng,
        ]);
        const line = L.polyline(coords, {
          color: "#1e2a5a",
          weight: 4,
          opacity: 0.85,
        }).addTo(map);
        map.fitBounds(line.getBounds(), { padding: [24, 24] });
        const mins = Math.round(route.duration / 60);
        const km = (route.distance / 1000).toFixed(1);
        linkWrap.innerHTML += ` <span class="map-meta">· aprox. ${mins} min · ${km} km</span>`;
      } catch {
        map.fitBounds(L.latLngBounds(markers.map((m) => m.getLatLng())), {
          padding: [32, 32],
        });
        linkWrap.innerHTML +=
          ' <span class="map-meta">· Ruta aproximada no disponible</span>';
      }
    } else {
      map.fitBounds(L.latLngBounds(markers.map((m) => m.getLatLng())), {
        padding: [40, 40],
        maxZoom: 6,
      });
      const note =
        mode === "flight"
          ? "Tramo aéreo: solo marcadores"
          : "Tramo en transporte público: consultá la ruta en Google Maps";
      linkWrap.innerHTML += ` <span class="map-meta">· ${note}</span>`;
    }
  } else if (markers.length) {
    map.setView(markers[0].getLatLng(), 15);
  }

  container.classList.add("is-ready");
  setTimeout(() => map.invalidateSize(), 80);
}

function costsHtml(costs) {
  if (!costs?.length) return "<p>Sin costos listados.</p>";
  return `<ul>${costs
    .map(
      (c) =>
        `<li>${escapeHtml(c.item)}: <strong>${formatMoney(c.amount, c.currency)}</strong>${
          c.perPerson ? " / persona" : ""
        }</li>`
    )
    .join("")}</ul>`;
}

function listBlock(title, items) {
  if (!items?.length) return "";
  return `<div><h4>${title}</h4><ul>${items
    .map((i) => `<li>${escapeHtml(i)}</li>`)
    .join("")}</ul></div>`;
}

function dayEssentialsHtml(essentials) {
  if (!essentials?.bring?.length && !essentials?.avoid?.length) return "";
  return `<section class="day-essentials" aria-label="Preparación para todo el día">
    <div class="day-essentials-heading">
      <span class="day-essentials-icon" aria-hidden="true">✓</span>
      <div>
        <p class="eyebrow">Una sola vez</p>
        <h2>Para todo el día</h2>
      </div>
    </div>
    <div class="lists">
      ${listBlock("Llevar", essentials.bring)}
      ${listBlock("Evitar", essentials.avoid)}
    </div>
  </section>`;
}

function sentenceItems(text) {
  if (!text?.trim()) return [];
  return text
    .trim()
    .split(/(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜ0-9])/u)
    .map((item) => item.trim())
    .filter(Boolean);
}

function guidanceHtml(ev, travelBits) {
  const route = [];
  if (ev.from && ev.to && !placesAreSame(ev.from, ev.to)) {
    route.push(`Salir de ${ev.from.name || "el origen"} hacia ${ev.to.name || "el destino"}.`);
  } else if (ev.category === "hotel") {
    route.push("Este bloque marca la llegada y la noche en el alojamiento; no es otro desplazamiento.");
  } else {
    route.push("La actividad comienza en el punto marcado en el mapa.");
  }
  if (travelBits) route.push(`${travelBits}.`);
  if (
    ev.travel?.notes &&
    !ev.travel.notes.startsWith("Sin coords") &&
    !route.some((item) => item.includes(ev.travel.notes))
  ) {
    route.push(ev.travel.notes);
  }

  const plan = sentenceItems(ev.description);
  return `<div class="guidance-grid">
    <section class="guidance-card route-guidance">
      <h4>Cómo llegar</h4>
      <ol>${route.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
    </section>
    <section class="guidance-card action-guidance">
      <h4>Qué hacer / decisiones</h4>
      ${
        plan.length
          ? `<ul>${plan.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
          : "<p>Sin instrucciones adicionales.</p>"
      }
    </section>
  </div>`;
}

function flagBadges(flags) {
  if (!flags?.length) return "";
  return flags
    .map((f) => {
      const sev = f.severity || "medium";
      const label = {
        critical: "Alerta",
        high: "Revisar",
        medium: "Nota",
        low: "Info",
      }[sev] || "Nota";
      return `<span class="badge flag flag-${escapeHtml(sev)}" title="${escapeHtml(f.message || "")}">${escapeHtml(label)}</span>`;
    })
    .join("");
}

function eventHtml(ev) {
  const inferred = ev.inferred
    ? '<span class="badge inferred">Horario inferido</span>'
    : "";
  const partial = (ev.participants || []).some((p) => !p.going)
    ? '<span class="badge partial">No todos van</span>'
    : "";
  const booking = bookingBadge(ev.bookingStatus);
  const flags = flagBadges(ev.flags);
  const track =
    ev.track && ev.track !== "all"
      ? `<span class="badge track">${escapeHtml(
          ev.track === "sergio_arley" ? "Sergio/Arley" : "Grupo Tokio"
        )}</span>`
      : "";
  const hasTravel =
    (ev.travel?.mode && ev.travel.mode !== "none") ||
    Number(ev.travel?.durationMin) > 0 ||
    Number(ev.travel?.distanceKm) > 0;
  const travelBits = hasTravel
    ? [
        ev.travel?.mode && ev.travel.mode !== "none" ? ev.travel.mode : null,
        Number(ev.travel?.durationMin) > 0
          ? `~${ev.travel.durationMin} min`
          : null,
        Number(ev.travel?.distanceKm) > 0
          ? `${ev.travel.distanceKm} km`
          : null,
        ev.travel?.line || null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";

  const image = ev.image
    ? `<figure style="margin:0;">
        <img class="event-image" src="${escapeHtml(ev.image)}" alt="${escapeHtml(ev.title)}" loading="lazy" />
        ${
          ev.imageCredit
            ? `<figcaption style="font-size:0.75rem;color:var(--muted);margin-top:0.35rem;">${escapeHtml(ev.imageCredit)}</figcaption>`
            : ""
        }
      </figure>`
    : "";
  const eventPacking =
    ev.bring?.length || ev.dontBring?.length
      ? `<div class="lists event-specific-lists">
          ${listBlock("Llevar para este evento", ev.bring)}
          ${listBlock("Evitar en este evento", ev.dontBring)}
        </div>`
      : "";

  const flagNotes = (ev.flags || [])
    .map(
      (f) =>
        `<li class="flag-note flag-${escapeHtml(f.severity || "medium")}"><strong>${escapeHtml(f.code)}</strong> — ${escapeHtml(f.message)}</li>`
    )
    .join("");

  return `<details class="event" data-event-id="${escapeHtml(ev.id)}">
    <summary>
      <div class="time-row">
        <span>${timeLabel(ev.start)} – ${timeLabel(ev.end)}</span>
        ${inferred}
        ${booking}
        ${partial}
        ${track}
        ${flags}
      </div>
      <h3>${escapeHtml(ev.title)}</h3>
      <span class="expand-hint"><span class="when-closed">Ver detalle ▾</span><span class="when-open">Ocultar detalle ▴</span></span>
    </summary>
    <div class="event-body">
      ${
        flagNotes
          ? `<ul class="flag-list">${flagNotes}</ul>`
          : ""
      }
      <div class="chips">${participantChips(ev.participants)}</div>
      <div class="event-map" id="map-${escapeHtml(ev.id)}"></div>
      <dl class="meta-grid">
        <div><dt>Desde</dt><dd>${
          ev.from && !placesAreSame(ev.from, ev.to)
            ? escapeHtml(ev.from.name || "—")
            : "—"
        }</dd></div>
        <div><dt>Hasta</dt><dd>${escapeHtml(ev.to?.name || "—")}</dd></div>
        <div><dt>Transporte</dt><dd>${escapeHtml(travelBits || "—")}</dd></div>
        <div><dt>Reserva</dt><dd>${escapeHtml(ev.bookingDetail || BOOKING_LABELS[ev.bookingStatus] || "—")}</dd></div>
      </dl>
      ${guidanceHtml(ev, travelBits)}
      ${image}
      <div>
        <h4 style="margin:0 0 0.4rem;font-size:0.8rem;letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);">Costos</h4>
        ${costsHtml(ev.costs)}
      </div>
      ${eventPacking}
      ${
        ev.reservation
          ? `<p style="font-size:0.9rem;color:var(--muted);margin:0;"><strong>Localizador / nota:</strong> ${escapeHtml(ev.reservation)}</p>`
          : ""
      }
    </div>
  </details>`;
}

async function main() {
  const data = await loadItinerary("../data/itinerary.json");
  const travelers = data.meta?.travelers || [];
  const personIds = readPersonFilter().filter((id) =>
    travelers.some((t) => t.id === id)
  );
  const filterQ = personFilterQuery(personIds);

  const back = document.querySelector(".day-hero .back");
  if (back) back.setAttribute("href", `../index.html${filterQ}`);

  const day = (data.days || []).find((d) => d.date === DAY_DATE);
  if (!day) {
    document.getElementById("day-root").innerHTML =
      `<p>No encontré el día ${DAY_DATE} en itinerary.json</p>`;
    return;
  }

  const events = filteredEvents(day, personIds);
  const dayIndex = data.days.findIndex((item) => item.date === DAY_DATE);
  const neighbors = document.getElementById("day-nav-neighbors");
  if (neighbors) {
    const previous = data.days[dayIndex - 1];
    const next = data.days[dayIndex + 1];
    neighbors.innerHTML = [
      previous
        ? `<a href="./${previous.date}.html${filterQ}">← Día ${dayIndex - 1}</a>`
        : "",
      next
        ? `<a href="./${next.date}.html${filterQ}">Día ${dayIndex + 1} →</a>`
        : "",
    ]
      .filter(Boolean)
      .join("");
  }

  document.title = `${day.title} · Viaje Japón`;
  document.getElementById("day-title").textContent = day.title;
  document.getElementById("day-date").textContent = formatDateEs(day.date);
  document.getElementById("day-summary").textContent = day.summary || "";
  const coverEvent =
    events.find((event) => event.category === "visita" && event.image) ||
    events.find((event) => event.image);
  const cover = document.getElementById("day-cover");
  if (cover && coverEvent) {
    const coverImage = document.getElementById("day-cover-image");
    const coverCaption = document.getElementById("day-cover-caption");
    coverImage.src = coverEvent.image;
    coverImage.alt = coverEvent.title;
    coverCaption.textContent = `${day.city || "En ruta"} · ${coverEvent.title}`;
    cover.hidden = false;
  }
  document.getElementById("stat-city").textContent = day.city || "—";
  const hotelStat = document.getElementById("stat-hotel");
  const splitHotel =
    day.hotel?.sergioArley && day.hotel.sergioArley !== "Con el grupo";
  const onlySergioArley =
    personIds.length > 0 &&
    personIds.every((id) => id === "sergio" || id === "arley");
  if (splitHotel && onlySergioArley) {
    hotelStat.textContent = day.hotel.sergioArley;
  } else if (splitHotel && personIds.length) {
    hotelStat.textContent = `Grupo: ${day.hotel.group || "—"} · Sergio/Arley: ${day.hotel.sergioArley}`;
  } else {
    hotelStat.textContent = day.hotel?.name || day.hotel?.group || "—";
  }
  const firstVisiblePlace = events
    .map((event) => placeToLatLng(event.to) || placeToLatLng(event.from))
    .find(Boolean);
  const mapDay = {
    ...day,
    events,
    hotel: splitHotel && onlySergioArley ? null : day.hotel,
    mapCenter:
      splitHotel && onlySergioArley && firstVisiblePlace
        ? firstVisiblePlace
        : day.mapCenter,
  };

  let essentials = document.getElementById("day-essentials");
  if (!essentials) {
    essentials = document.createElement("div");
    essentials.id = "day-essentials";
    const hero = document.querySelector(".day-hero");
    const dayMap = document.getElementById("day-map");
    if (hero && dayMap) hero.insertBefore(essentials, dayMap);
  }
  essentials.innerHTML = dayEssentialsHtml(day.dayEssentials);
  essentials.hidden = !essentials.innerHTML;

  // Risk banner (sleep_risk etc.)
  let riskBanner = document.getElementById("risk-banner");
  if (!riskBanner) {
    riskBanner = document.createElement("div");
    riskBanner.id = "risk-banner";
    riskBanner.className = "risk-banner";
    const hero = document.querySelector(".day-hero");
    const dayMap = document.getElementById("day-map");
    if (hero && dayMap) hero.insertBefore(riskBanner, dayMap);
    else if (hero) hero.appendChild(riskBanner);
  }
  const criticalMsgs = [
    ...(day.dayFlags || []),
    ...events.flatMap((e) => e.flags || []),
  ].filter((f) => f.severity === "critical");
  if (criticalMsgs.length) {
    riskBanner.hidden = false;
    const uniq = [];
    const seen = new Set();
    for (const f of criticalMsgs) {
      if (seen.has(f.code)) continue;
      seen.add(f.code);
      uniq.push(f);
    }
    riskBanner.innerHTML = `<strong>Alertas del día</strong><ul>${uniq
      .map(
        (f) =>
          `<li><span class="badge flag flag-critical">${escapeHtml(f.code)}</span> ${escapeHtml(f.message)}</li>`
      )
      .join("")}</ul>`;
  } else {
    riskBanner.hidden = true;
    riskBanner.innerHTML = "";
  }

  const totals = filteredDayTotals(
    day,
    events,
    personIds,
    data.meta?.fxJPY_to_COP || 21
  );
  document.getElementById("stat-jpy").textContent = formatMoney(totals.jpy, "JPY");
  document.getElementById("stat-cop").textContent = formatMoney(totals.cop, "COP");

  const warn = document.getElementById("maps-warn");
  if (warn) {
    warn.hidden = Boolean(window.L);
    warn.textContent = window.L
      ? ""
      : "El mapa no pudo cargar, pero el itinerario y los enlaces de Google Maps siguen disponibles.";
  }
  const dayMap = document.getElementById("day-map");
  if (dayMap && !window.L) dayMap.hidden = true;

  let banner = document.getElementById("filter-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "filter-banner";
    banner.className = "filter-banner";
    const hero = document.querySelector(".day-hero");
    const dayMap = document.getElementById("day-map");
    if (hero && dayMap) hero.insertBefore(banner, dayMap);
    else if (hero) hero.appendChild(banner);
  }
  if (personIds.length) {
    const names = personIds.map((id) => {
      const t = travelers.find((x) => x.id === id);
      return t ? shortName(t) : id;
    });
    banner.hidden = false;
    banner.innerHTML = `Mostrando ${events.length} evento${events.length === 1 ? "" : "s"} de <strong>${escapeHtml(names.join(", "))}</strong>. <a href="../index.html${filterQ}">Cambiar filtro</a> · <a href="./${DAY_DATE}.html">Ver día completo</a>`;
  } else {
    banner.hidden = true;
    banner.innerHTML = "";
  }

  const eventsEl = document.getElementById("events");
  if (!events.length) {
    eventsEl.innerHTML =
      '<p style="color:var(--muted);">Nadie del filtro participa en eventos este día.</p>';
    if (dayMap) dayMap.hidden = true;
    return;
  }

  eventsEl.innerHTML = events.map(eventHtml).join("");
  initDayMap(mapDay);

  eventsEl.querySelectorAll("details.event").forEach((details) => {
    details.addEventListener("toggle", () => {
      if (!details.open) return;
      const id = details.dataset.eventId;
      const ev = events.find((e) => e.id === id);
      const mapEl = document.getElementById(`map-${id}`);
      if (ev && mapEl) renderEventMap(ev, mapEl);
    });
  });
}

main().catch((err) => {
  console.error(err);
  const root = document.getElementById("day-root");
  if (root) {
    root.innerHTML = `<p style="color:#a33b1a;">Error: ${err.message}</p>`;
  }
});
