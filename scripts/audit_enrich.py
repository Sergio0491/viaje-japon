"""Post-process itinerary days: tracks, city labels, Kyoto remap, flags, reflow, audit.json."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

EARLY_EXIT_IDS = ("pipe", "mafalda", "julian")
EARLY_EXIT_FROM = "2026-11-17"  # leave night of 16 → absent from 17 onward


def flag(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def parse_hm(s: str | None) -> int | None:
    if not s or ":" not in s:
        return None
    try:
        h, m = map(int, s.split(":")[:2])
        return h * 60 + m
    except ValueError:
        return None


def fmt_hm(mins: int) -> str:
    mins = max(0, mins)
    # Cap display at 23:59 for same-calendar-day timeline (avoid 25:xx)
    if mins >= 24 * 60:
        mins = 23 * 60 + 59
    return f"{mins // 60:02d}:{mins % 60:02d}"


def is_generic_transport(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t:
        return False
    # Exact / near-exact Excel placeholders — not real legs
    if t in ("transporte publico", "transporte público"):
        return True
    if t.startswith("transporte publico") and len(t) < 28:
        return True
    if t.startswith("transporte público") and len(t) < 28:
        return True
    return False


def assign_track(date: str, title: str, category: str, participants: list | None) -> str:
    t = (title or "").lower()
    going = {p["id"] for p in (participants or []) if p.get("going")}

    # Explicit Sergio/Arley transit before reunion
    if date <= "2026-10-31":
        if category == "vuelo" or "hyatt" in t or "lax" in t or "narita" in t and "sq" in t:
            return "sergio_arley"
        if going and going <= {"sergio", "arley"}:
            return "sergio_arley"
        if going and "sergio" not in going and "arley" not in going:
            return "group_tokyo"
        # Mixed / ambiguous on dual days → group for Tokyo sightseeing, sergio for flights
        if any(k in t for k in ("ueno", "senso", "skytree", "ikebukuro", "yanaka", "nezu", "ameyoko", "halloween")):
            return "group_tokyo"
        if category in ("vuelo",) or "vuelo" in t:
            return "sergio_arley"
        return "group_tokyo"

    if date == "2026-11-01":
        if going and going <= {"sergio", "arley"}:
            return "sergio_arley"
        if any(k in t for k in ("narita", "tobu", "llegada", "senso-ji de noche", "sensoji de noche")):
            return "sergio_arley"
        if any(k in t for k in ("palacio", "kabuki", "pokemon", "akihabara")):
            return "group_tokyo"
        return "group_tokyo"

    if date == "2026-11-02" and "daikoku" in t:
        return "sergio_arley"  # night subgroup; keep separate from hotel endOfDay chain

    return "all"


def strip_early_exit(participants: list, date: str) -> list:
    if date < EARLY_EXIT_FROM:
        return participants
    out = []
    for p in participants:
        p = dict(p)
        if p.get("id") in EARLY_EXIT_IDS:
            p["going"] = False
            p["reason"] = p.get("reason") or "Salen la noche del 16 de noviembre"
        out.append(p)
    return out


def city_for_date(date: str, fallback: str = "") -> str:
    if date <= "2026-11-02":
        return "Tokio"
    if date in ("2026-11-03",):
        return "Fujiyoshida / Kawaguchiko"
    if date == "2026-11-04":
        return "Kawaguchiko → Kioto"
    if date in ("2026-11-05", "2026-11-06"):
        return "Kioto"
    if "2026-11-07" <= date <= "2026-11-10":
        return "Osaka"
    if date == "2026-11-11":
        return "Osaka → Nagoya → Kanazawa"
    if "2026-11-12" <= date <= "2026-11-13":
        return "Kanazawa"
    if "2026-11-14" <= date <= "2026-11-17":
        return "Tokio"
    if date == "2026-11-18":
        return "Tokio → LAX"
    # Fix truncated Excel labels
    fb = fallback or ""
    if fb.startswith("Kansai"):
        return "Kioto" if date <= "2026-11-06" else "Osaka"
    if fb.startswith("Tokio"):
        return "Tokio"
    if fb.startswith("Mt"):
        return "Fujiyoshida / Kawaguchiko"
    return fb or "Japón"


def fix_city_labels(day_list: list[dict]) -> None:
    for d in day_list:
        date = d["date"]
        city = city_for_date(date, d.get("city") or "")
        d["city"] = city
        # Rebuild title city segment if it still has Excel garbage
        title = d.get("title") or ""
        title_l = title.lower()
        if "kansai" in title_l or "tokio v" in title_l or "mt. fuji" in title_l or "mt.fuji" in title_l:
            parts = title.split(" — ", 1)
            prefix = parts[0] if len(parts) == 2 else title.split(" ", 2)[0]
            day_label = ""
            if "(" in title and title.rstrip().endswith(")"):
                day_label = title[title.rfind("(") :]
            d["title"] = f"{prefix} — {city} {day_label}".strip()
        elif "Kansai" in (d.get("city") or ""):
            d["city"] = city


def fix_kyoto_nov5(day_list: list[dict]) -> None:
    """Remap broken 01:xx / 03:xx / 04:xx Excel times to coherent afternoon/evening."""
    target = next((d for d in day_list if d["date"] == "2026-11-05"), None)
    if not target:
        return
    slots = [
        (("castillo",), "13:50", "15:20"),
        (("baño", "baños", "banos public", "baños public"), "16:00", "17:30"),
        (("calle pontocho", "calle pontochō"), "18:30", "20:30"),
    ]
    for ev in target["events"]:
        t = (ev.get("title") or "").lower()
        start = parse_hm(ev.get("start"))
        matched = False
        for keys, s, e in slots:
            if any(k in t for k in keys):
                if "castillo" in keys and "castillo" not in t:
                    continue
                # Don't remap pure transit legs that only name a place as endpoint
                if ev.get("category") == "transporte" and not any(
                    k in t for k in ("baño", "baños", "calle pontocho", "calle pontochō")
                ):
                    continue
                ev["start"], ev["end"] = s, e
                ev["inferred"] = True
                ev["scheduleLocked"] = True
                matched = True
                break
        if matched:
            continue
        # Generic: any remaining start < 06:00 on this day → bump +12h
        st = parse_hm(ev.get("start"))
        en = parse_hm(ev.get("end"))
        if st is not None and st < 6 * 60 and ev.get("category") != "transporte":
            ev["start"] = fmt_hm(st + 12 * 60)
            if en is not None and en < 8 * 60:
                ev["end"] = fmt_hm(en + 12 * 60)
            ev["inferred"] = True
            ev["scheduleLocked"] = True
    target.setdefault("dayFlags", []).append(
        flag("medium", "packed_day", "Arashiyama → Otagi → Kinkaku → Nijo: día largo clásico; priorizar y recortar si hace falta.")
    )


def mark_hotels_end_of_day(events: list[dict]) -> None:
    for ev in events:
        if ev.get("category") == "hotel":
            ev["endOfDay"] = True


def infer_times_by_track(events: list[dict]) -> None:
    """Fill missing times per track so dual-track days never chain into 25:xx."""
    mark_hotels_end_of_day(events)
    by_track: dict[str, list] = {}
    for ev in events:
        track = ev.get("track") or "all"
        by_track.setdefault(track, []).append(ev)

    for track, track_events in by_track.items():
        # Sort known-time events first for cursor seeding; process in list order within unknowns
        ordered = sorted(
            track_events,
            key=lambda e: (
                0 if e.get("endOfDay") else 1,
                parse_hm(e.get("start")) if parse_hm(e.get("start")) is not None else 10**9,
            ),
        )
        # Walk in original relative order excluding endOfDay hotels for cursor
        timeline = [e for e in track_events if not e.get("endOfDay")]
        cursor = 9 * 60
        for ev in timeline:
            st = parse_hm(ev.get("start"))
            en = parse_hm(ev.get("end"))
            if st is not None:
                # Clamp absurd Excel hours (>24) from prior bugs if any slip through as strings
                if st >= 24 * 60:
                    st = st % (24 * 60)
                    ev["start"] = fmt_hm(st)
                    ev["inferred"] = True
                cursor = st
                if en is not None:
                    if en >= 24 * 60:
                        en = min(en, 23 * 60 + 59)
                        ev["end"] = fmt_hm(en)
                        ev["inferred"] = True
                    # Cross-midnight flights: keep as-is
                    if en >= st or ev.get("category") == "vuelo":
                        cursor = en if en >= st else st + 60
                    else:
                        cursor = st + 60
                else:
                    cursor = st + 60
                continue
            # Assign new slot
            dur = 60
            mode = (ev.get("travel") or {}).get("mode")
            if mode in ("tren", "bus", "metro"):
                dur = max(45, (ev.get("travel") or {}).get("durationMin") or 45)
            elif ev.get("category") == "visita":
                dur = 90
            elif ev.get("category") == "transporte":
                dur = 45
            elif ev.get("category") == "vuelo":
                dur = 180
            # Keep within same calendar evening (≤ 23:30 start)
            if cursor > 23 * 60 + 30:
                cursor = 21 * 60
            start_m = cursor
            end_m = min(start_m + dur, 23 * 60 + 59)
            ev["start"] = fmt_hm(start_m)
            ev["end"] = fmt_hm(end_m)
            ev["inferred"] = True
            cursor = end_m + 15

        # Hotels / endOfDay: place after last timeline event of same track (or 22:30)
        last_end = 22 * 60 + 30
        for ev in timeline:
            en = parse_hm(ev.get("end")) or parse_hm(ev.get("start"))
            if en is not None:
                last_end = max(last_end, min(en, 23 * 60 + 30))
        for ev in track_events:
            if not ev.get("endOfDay"):
                continue
            if not ev.get("start") or parse_hm(ev.get("start")) is None:
                # Don't collide with late nightlife on same track — after last, capped
                hs = min(max(last_end + 10, 22 * 60), 23 * 60 + 40)
                ev["start"] = fmt_hm(hs)
                ev["end"] = fmt_hm(min(hs + 30, 23 * 60 + 59))
                ev["inferred"] = True
            # If hotel was hard-coded 22:00 but night events go later, push hotel after
            night_ends = [
                parse_hm(e.get("end")) or 0
                for e in timeline
                if (parse_hm(e.get("start")) or 0) >= 19 * 60
            ]
            if night_ends:
                after = max(night_ends) + 5
                if after < 24 * 60 and (parse_hm(ev.get("start")) or 0) < after:
                    ev["start"] = fmt_hm(min(after, 23 * 60 + 40))
                    ev["end"] = fmt_hm(min(after + 20, 23 * 60 + 59))
                    ev["inferred"] = True


def reflow_buffers(events: list[dict]) -> None:
    """When Excel lacks times (inferred), ensure gap ≥ travel + 10 within each track."""
    by_track: dict[str, list] = {}
    for ev in events:
        if ev.get("endOfDay") or ev.get("category") == "comida":
            continue
        by_track.setdefault(ev.get("track") or "all", []).append(ev)

    for track_events in by_track.values():
        seq = sorted(
            track_events,
            key=lambda e: parse_hm(e.get("start")) if parse_hm(e.get("start")) is not None else 10**9,
        )
        for i in range(1, len(seq)):
            prev, cur = seq[i - 1], seq[i]
            # Only reflow inferred events (don't move reserved trains/flights)
            if cur.get("scheduleLocked"):
                continue
            if not cur.get("inferred") and parse_hm(cur.get("start")) is not None:
                # Still check gap for flagging later; don't move fixed times
                continue
            if not cur.get("inferred"):
                continue
            prev_end = parse_hm(prev.get("end")) or parse_hm(prev.get("start"))
            cur_start = parse_hm(cur.get("start"))
            if prev_end is None or cur_start is None:
                continue
            need = ((cur.get("travel") or {}).get("durationMin") or 0) + 10
            gap = cur_start - prev_end
            if gap >= need:
                continue
            shift = need - gap
            new_start = cur_start + shift
            dur = max(
                30,
                (parse_hm(cur.get("end")) or (cur_start + 60)) - cur_start,
            )
            if new_start + dur > 23 * 60 + 59:
                # Can't fit — leave and let flags mark tight buffer
                continue
            cur["start"] = fmt_hm(new_start)
            cur["end"] = fmt_hm(new_start + dur)
            cur["reflowed"] = True


def chain_skip_placeholders(events: list[dict], day_hotel_place: dict | None, chain_fn) -> None:
    """Chain only mappable events; placeholders already removed from list."""
    chain_fn(events, day_hotel_place)


def apply_event_flags(day: dict) -> None:
    date = day["date"]
    events = day.get("events") or []
    day_flags: list[dict] = list(day.get("dayFlags") or [])

    for ev in events:
        ev.setdefault("flags", [])
        t = (ev.get("title") or "").lower()
        detail = (ev.get("bookingDetail") or "").lower()

        # C1 sleep risk — resuelto con el tour 17:30 si el regreso es al hotel
        if date == "2026-11-02" and "daikoku" in t:
            ev["flags"].append(
                flag(
                    "medium",
                    "confirm_dropoff",
                    "Sueño resuelto si Tokyo Turismo los deja en el Tobu Levant (Kinshicho), no solo en Shibuya. Pedirlo por WhatsApp al +81 90 8383 5525. Tour 17:30–~21:30, GYGFWVYL2943.",
                )
            )
            day_flags.append(ev["flags"][-1])
        if date == "2026-11-03" and ("fuji-excursion" in t or "fuji excursion" in t):
            ev["flags"].append(
                flag(
                    "low",
                    "sleep_risk",
                    "Resuelto: el tour del 2 termina ~21:30. Omitir Oishi si queda cansancio. Yamato ~05:45 y tren 07:07 siguen en pie.",
                )
            )

        # C2 capacity — resolved: Sebastián completó las otras 4 reservas (8/8)
        if "fuji-excursion" in t or "fuji excursion" in t or "e90632" in detail:
            if "4/8" in (ev.get("bookingDetail") or "") or "solo 4" in (ev.get("bookingDetail") or "").lower():
                ev["bookingDetail"] = (
                    "E90632 (4) + segunda reserva Sebastián (4) — 8/8 asientos confirmados · "
                    "carro 2, 8A/8B/9A/9B en E90632 · pickup 31212393070521258"
                )
            ev["bookingStatus"] = "ready"
            # Strip stale capacity wording from description
            desc = ev.get("description") or ""
            for stale in (
                "⚠ La reserva actual cubre solo 4 de 8 personas.",
                "solo 4 de 8 personas",
            ):
                desc = desc.replace(stale, "").strip()
            if "8/8" not in desc and "ocho" not in desc.lower():
                desc = (desc + " Los ocho van: E90632 + reserva adicional de Sebastián.").strip()
            ev["description"] = desc

        # C3 bus Mishima — only the Kawaguchiko→Mishima reserved bus
        if date == "2026-11-04" and "mishima" in t and "bus" in t and "shinkansen" not in t:
            ev["flags"].append(
                flag(
                    "critical",
                    "urgent_booking",
                    "Bus Kawaguchiko→Mishima 14:00: reservar en Fujiyama Connect (~¥2500). Sin localizador aún.",
                )
            )
            ev["bookingStatus"] = "needs_reservation"

        # C4 hotels payment
        if ev.get("category") == "hotel" and any(
            k in t for k in ("kioto", "kyoto", "kanazawa", "yoyogi")
        ):
            if ev.get("bookingStatus") == "needs_reservation" or "confirmar" in detail:
                ev["flags"].append(
                    flag(
                        "critical",
                        "confirm_payment",
                        "Hotel con dirección pero pago/confirmación pendiente (no marcar listo).",
                    )
                )

        # C5 USJ underspecified
        if "universal" in t or "usj" in t:
            ev["flags"].append(
                flag(
                    "critical",
                    "underspecified",
                    "USJ modelado demasiado corto en Excel — tratar como día completo / comodín, no bloque de 90 min.",
                )
            )
            if ev.get("inferred") or (parse_hm(ev.get("end")) or 0) - (parse_hm(ev.get("start")) or 0) < 180:
                if not ev.get("start"):
                    ev["start"], ev["end"] = "09:30", "18:00"
                else:
                    st = parse_hm(ev.get("start")) or 9 * 60 + 30
                    ev["end"] = fmt_hm(min(st + 8 * 60, 20 * 60))
                ev["inferred"] = True
                ev["description"] = (
                    (ev.get("description") or "")
                    + " Día de parque: planificar Express Pass / horarios reales; no es una visita corta."
                )

        # Medium geography / pace
        if date == "2026-11-08" and ("nara" in t or "tōdai" in t or "todai" in t):
            st = parse_hm(ev.get("start"))
            if st is not None and st <= 8 * 60:
                ev["flags"].append(
                    flag("medium", "tight", "Hotel→Nara temprano: dejar buffer de metro; 08:00 en Tōdai-ji es justo.")
                )
        if date == "2026-11-09" and ("fushimi" in t or "daigo" in t or "biovortex" in t):
            ev["flags"].append(
                flag(
                    "medium",
                    "tight",
                    "Fushimi + Daigo + Biovortex 14:30: viable si se recorta Daigo.",
                )
            )
        if date == "2026-11-15" and "meiji" in t:
            ev["flags"].append(
                flag(
                    "medium",
                    "crowded",
                    "Meiji en Shichi-Go-San: muchedumbre esperada; llegar temprano o acortar.",
                )
            )
        if date == "2026-11-18" and ev.get("category") == "vuelo":
            st, en = parse_hm(ev.get("start")), parse_hm(ev.get("end"))
            if st is not None and en is not None and en < st:
                ev["flags"].append(
                    flag(
                        "medium",
                        "crosses_midnight",
                        "Horario de llegada en LA es del día calendario siguiente (cruza medianoche). No es un error de end<start.",
                    )
                )

        # Buffer tightness vs travel
        # (computed in day pass below)

    # Day-level: Nov 2 zigzag note
    if date == "2026-11-02":
        day_flags.append(
            flag(
                "medium",
                "zigzag",
                "Los ocho van a Roppongi hasta las 16:15. Después: tour (Sergio, Arley, Pipe, Johan) o Torre (el resto). La vuelta al hotel es un trayecto aparte.",
            )
        )
    if date == "2026-11-11":
        day_flags.append(
            flag(
                "medium",
                "transfer_only",
                "Nagoya ~5 h entre trenes — escala de conexión, no sightseeing inventado.",
            )
        )

    # Pairwise buffer gaps within track
    by_track: dict[str, list] = {}
    for ev in events:
        if ev.get("endOfDay"):
            continue
        by_track.setdefault(ev.get("track") or "all", []).append(ev)
    for track_events in by_track.values():
        seq = sorted(
            [e for e in track_events if parse_hm(e.get("start")) is not None],
            key=lambda e: parse_hm(e.get("start")) or 0,
        )
        for i in range(1, len(seq)):
            prev, cur = seq[i - 1], seq[i]
            prev_going = {p["id"] for p in prev.get("participants") or [] if p.get("going")}
            cur_going = {p["id"] for p in cur.get("participants") or [] if p.get("going")}
            if prev_going and cur_going and not (prev_going & cur_going):
                continue
            prev_end = parse_hm(prev.get("end")) or parse_hm(prev.get("start")) or 0
            cur_start = parse_hm(cur.get("start")) or 0
            cur_end = parse_hm(cur.get("end")) or cur_start
            ride = (cur.get("travel") or {}).get("durationMin") or 0
            gap = cur_start - prev_end
            # A displacement event is the ride. The slot has to cover it.
            # Don't also demand that same ride as free time before it starts.
            if cur.get("travelRole") == "leg":
                span = cur_end - cur_start
                if span + 5 < ride:
                    cur.setdefault("flags", []).append(
                        flag(
                            "high",
                            "tight_buffer",
                            f"El trayecto dura ~{ride} min y el hueco del evento es {span} min.",
                        )
                    )
                continue
            # The tour's drive happens after the meeting point, inside the booking.
            if cur.get("travelInside"):
                continue
            need = ride + 10
            if need > 15 and gap < need and cur.get("category") != "vuelo":
                cur.setdefault("flags", []).append(
                    flag(
                        "high",
                        "tight_buffer",
                        f"Hueco {gap} min < trayecto estimado {need - 10} min + 10. Revisar orden o recortar.",
                    )
                )

    # Dedupe day flags by code
    seen = set()
    uniq = []
    for f in day_flags:
        if f["code"] in seen:
            continue
        seen.add(f["code"])
        uniq.append(f)
    day["dayFlags"] = uniq


def enrich_injected_tracks(day_list: list[dict]) -> None:
    for d in day_list:
        for ev in d.get("events") or []:
            if "track" not in ev:
                ev["track"] = assign_track(
                    d["date"], ev.get("title") or "", ev.get("category") or "", ev.get("participants")
                )
            ev.setdefault("flags", [])
            if ev.get("participants"):
                ev["participants"] = strip_early_exit(ev["participants"], d["date"])


def build_audit_summary(day_list: list[dict]) -> dict:
    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for d in day_list:
        for f in d.get("dayFlags") or []:
            item = {
                "date": d["date"],
                "dayTitle": d.get("title"),
                "eventId": None,
                "eventTitle": None,
                **f,
            }
            by_severity.setdefault(f["severity"], []).append(item)
        for ev in d.get("events") or []:
            for f in ev.get("flags") or []:
                item = {
                    "date": d["date"],
                    "dayTitle": d.get("title"),
                    "eventId": ev.get("id"),
                    "eventTitle": ev.get("title"),
                    **f,
                }
                by_severity.setdefault(f["severity"], []).append(item)
    counts = {k: len(v) for k, v in by_severity.items()}
    return {
        "generatedFor": "itinerary expert audit",
        "counts": counts,
        "flags": by_severity,
    }


def enrich_days(day_list: list[dict], chain_fn, travel_fn, hotel_place_fn) -> dict:
    """
    Full post-inject enrichment pipeline.
    chain_fn / travel_fn / hotel_place_fn come from build_itinerary (no circular import).
    """
    # Drop generic transporte placeholders from all days
    for d in day_list:
        kept = []
        notes = []
        for ev in d.get("events") or []:
            if is_generic_transport(ev.get("title") or ""):
                notes.append(ev.get("title"))
                continue
            kept.append(ev)
        d["events"] = kept
        if notes:
            d["transitNote"] = (
                "Trayectos locales genéricos del Excel omitidos del timeline; usar Suica entre paradas."
            )

    enrich_injected_tracks(day_list)
    fix_city_labels(day_list)
    fix_kyoto_nov5(day_list)

    for d in day_list:
        date = d["date"]
        infer_times_by_track(d["events"])

        def sort_key(e):
            s = parse_hm(e.get("start"))
            if s is None:
                return (1, 10**9, 1 if e.get("endOfDay") else 0)
            return (0, s, 1 if e.get("endOfDay") else 0)

        d["events"].sort(key=sort_key)
        hotel_place = hotel_place_fn(date, d)

        by_track: dict[str, list] = {}
        for ev in d["events"]:
            by_track.setdefault(ev.get("track") or "all", []).append(ev)
        for track_evs in by_track.values():
            chain_fn(track_evs, hotel_place)
        travel_fn(d["events"])
        reflow_buffers(d["events"])
        d["events"].sort(key=sort_key)
        apply_event_flags(d)

        if date == "2026-11-03":
            d["summary"] = (
                (d.get("summary") or "")
                + " El tour del 2 termina ~21:30 si el regreso es al hotel. Oishi se omite si hay cansancio."
            ).strip()

    return build_audit_summary(day_list)


def write_audit_json(audit: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
