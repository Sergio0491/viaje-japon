#!/usr/bin/env python3
"""Build itinerary.json for the Japan trip static site from Excel + trip notes."""

from __future__ import annotations

import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

EXCEL = Path("/Users/sergio.valencia/Documents/viaje-japon/fuente/Akihabara 100% real no fake.xlsx")
OUT = Path("/Users/sergio.valencia/Documents/viaje-japon/web/data/itinerary.json")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
JPY_TO_COP = 21
USD_TO_COP = 3350

TRAVELERS = [
    {"id": "sergio", "name": "Sergio Valencia", "short": "Sergio"},
    {"id": "arley", "name": "Arley Vásquez", "short": "Arley"},
    {"id": "pipe", "name": "Pipe Escobar", "short": "Pipe"},
    {"id": "johan", "name": "Johan Bolívar", "short": "Johan"},
    {"id": "julian", "name": "Julián Otalvaro", "short": "Julián"},
    {"id": "mafalda", "name": "Mafalda", "short": "Mafalda"},
    {"id": "tatiana", "name": "Tatiana Betancur", "short": "Tati"},
    {"id": "sebastian", "name": "Sebastián Vargas", "short": "Sebas"},
]

ALL_IDS = [t["id"] for t in TRAVELERS]

PLACES = {
    "establishment_asakusa": {
        "name": "Establishment Asakusa",
        "query": "Establishment Asakusa, 3-28-21 Oshiage, Sumida, Tokyo",
        "lat": 35.7107777,
        "lng": 139.8144724,
    },
    "tobu_levant": {
        "name": "Tobu Hotel Levant Tokyo",
        "query": "Tobu Hotel Levant Tokyo, 1-2-2 Kinshi, Sumida",
        "lat": 35.6965,
        "lng": 139.8145,
    },
    "narita_t1": {
        "name": "Narita Airport Terminal 1",
        "query": "Narita International Airport Terminal 1",
        "lat": 35.7720,
        "lng": 140.3929,
    },
    "kinshicho": {
        "name": "Estación Kinshicho",
        "query": "Kinshicho Station Tokyo",
        "lat": 35.6962,
        "lng": 139.8139,
    },
    "oshiage": {
        "name": "Estación Oshiage",
        "query": "Oshiage Station Tokyo",
        "lat": 35.7107,
        "lng": 139.8130,
    },
    "sensoji": {
        "name": "Senso-ji",
        "query": "Senso-ji Temple Asakusa Tokyo",
        "lat": 35.7148,
        "lng": 139.7967,
    },
    "skytree": {
        "name": "Tokyo Skytree",
        "query": "Tokyo Skytree",
        "lat": 35.7101,
        "lng": 139.8107,
    },
    "ueno": {
        "name": "Ueno Park",
        "query": "Ueno Park Tokyo",
        "lat": 35.7142,
        "lng": 139.7731,
    },
    "tokyo_museum": {
        "name": "Museo Nacional de Tokio",
        "query": "Tokyo National Museum",
        "lat": 35.7188,
        "lng": 139.7765,
    },
    "ameyoko": {
        "name": "Ameyoko Market",
        "query": "Ameya-Yokocho Tokyo",
        "lat": 35.7097,
        "lng": 139.7745,
    },
    "nezu": {
        "name": "Santuario Nezu",
        "query": "Nezu Shrine Tokyo",
        "lat": 35.7202,
        "lng": 139.7608,
    },
    "yanaka": {
        "name": "Yanaka Ginza",
        "query": "Yanaka Ginza Tokyo",
        "lat": 35.7270,
        "lng": 139.7670,
    },
    "ikebukuro": {
        "name": "Ikebukuro",
        "query": "Ikebukuro Station Tokyo",
        "lat": 35.7295,
        "lng": 139.7109,
    },
    "imperial": {
        "name": "Palacio Imperial",
        "query": "Tokyo Imperial Palace East Gardens",
        "lat": 35.6852,
        "lng": 139.7528,
    },
    "kabukiza": {
        "name": "Kabuki-za",
        "query": "Kabuki-za Theatre Ginza",
        "lat": 35.6696,
        "lng": 139.7679,
    },
    "pokemon_center": {
        "name": "Pokémon Center Shibuya",
        "query": "Pokemon Center SHIBUYA Parco",
        "lat": 35.6618,
        "lng": 139.6993,
    },
    "akihabara": {
        "name": "Akihabara",
        "query": "Akihabara Electric Town Tokyo",
        "lat": 35.7023,
        "lng": 139.7745,
    },
    "tsukiji": {
        "name": "Mercado de Tsukiji (Outer)",
        "query": "Tsukiji Outer Market Tokyo",
        "lat": 35.6654,
        "lng": 139.7707,
    },
    "odaiba": {
        "name": "Odaiba",
        "query": "Odaiba Tokyo",
        "lat": 35.6297,
        "lng": 139.7753,
    },
    "roppongi": {
        "name": "Roppongi Hills",
        "query": "Roppongi Hills Tokyo",
        "lat": 35.6604,
        "lng": 139.7292,
    },
    "tokyo_tower": {
        "name": "Torre de Tokio",
        "query": "Tokyo Tower",
        "lat": 35.6586,
        "lng": 139.7454,
    },
    "kawaguchiko": {
        "name": "Estación Kawaguchiko",
        "query": "Kawaguchiko Station",
        "lat": 35.4983,
        "lng": 138.7685,
    },
    "ropeway": {
        "name": "Mt. Fuji Panoramic Ropeway",
        "query": "Mt Fuji Panoramic Ropeway Kawaguchiko",
        "lat": 35.5125,
        "lng": 138.7575,
    },
    "yurari": {
        "name": "Fuji Yurari Onsen",
        "query": "Fuji Yurari Hot Spring",
        "lat": 35.4875,
        "lng": 138.7940,
    },
    "fujiyoshida_airbnb": {
        "name": "Airbnb Fujiyoshida",
        "query": "2-6-10 Shinmachi Fujiyoshida Yamanashi",
        "lat": 35.497346,
        "lng": 138.8024018,
    },
    "chureito": {
        "name": "Pagoda Chureito",
        "query": "Chureito Pagoda Fujiyoshida",
        "lat": 35.5009,
        "lng": 138.8024,
    },
    "mishima": {
        "name": "Estación Mishima",
        "query": "Mishima Station Shizuoka",
        "lat": 35.1265,
        "lng": 138.9109,
    },
    "kyoto_hotel": {
        "name": "Hotel Kioto (Kariganecho)",
        "query": "409-1 Kariganecho Shimogyo Kyoto",
        "lat": 35.0017762,
        "lng": 135.7487804,
    },
    "arashiyama": {
        "name": "Bosque de bambú Arashiyama",
        "query": "Arashiyama Bamboo Grove Kyoto",
        "lat": 35.0170,
        "lng": 135.6721,
    },
    "tenryuji": {
        "name": "Tenryu-ji",
        "query": "Tenryu-ji Temple Kyoto",
        "lat": 35.0159,
        "lng": 135.6737,
    },
    "otagi": {
        "name": "Otagi Nenbutsu-ji",
        "query": "Otagi Nenbutsu-ji Kyoto",
        "lat": 35.0315,
        "lng": 135.6615,
    },
    "kinkakuji": {
        "name": "Kinkaku-ji",
        "query": "Kinkaku-ji Golden Pavilion Kyoto",
        "lat": 35.0394,
        "lng": 135.7292,
    },
    "nijo": {
        "name": "Castillo Nijō",
        "query": "Nijo Castle Kyoto",
        "lat": 35.0142,
        "lng": 135.7482,
    },
    "pontocho": {
        "name": "Calle Pontocho",
        "query": "Pontocho Alley Kyoto",
        "lat": 35.0047,
        "lng": 135.7710,
    },
    "kiyomizu": {
        "name": "Kiyomizu-dera",
        "query": "Kiyomizu-dera Kyoto",
        "lat": 34.9949,
        "lng": 135.7850,
    },
    "gion": {
        "name": "Gion / Yasaka",
        "query": "Yasaka Shrine Gion Kyoto",
        "lat": 35.0036,
        "lng": 135.7786,
    },
    "osaka_airbnb": {
        "name": "Airbnb Osaka Nipponbashi",
        "query": "2-10-5 Nipponbashi Chuo Osaka",
        "lat": 34.6641316,
        "lng": 135.5064371,
    },
    "nara": {
        "name": "Templo Tōdai-ji",
        "query": "Todai-ji Nara",
        "lat": 34.6889,
        "lng": 135.8398,
    },
    "fushimi": {
        "name": "Fushimi Inari",
        "query": "Fushimi Inari Taisha Kyoto",
        "lat": 34.9671,
        "lng": 135.7727,
    },
    "biovortex": {
        "name": "teamLab Biovortex Kyoto",
        "query": "teamLab Biovortex Kyoto",
        "lat": 34.9875,
        "lng": 135.7595,
    },
    "kanazawa_airbnb": {
        "name": "Airbnb Kanazawa",
        "query": "2-12 Kasaichimachi Kanazawa",
        "lat": 36.5769533,
        "lng": 136.6550447,
    },
    "kenrokuen": {
        "name": "Kenroku-en",
        "query": "Kenrokuen Garden Kanazawa",
        "lat": 36.5620,
        "lng": 136.6625,
    },
    "yoyogi_hotel": {
        "name": "Hotel Yoyogi Uehara",
        "query": "Hotel Yoyogi Uehara 17 Oyamacho Shibuya",
        "lat": 35.6682854,
        "lng": 139.6706681,
    },
    "yoyogi_park": {
        "name": "Yoyogi Park",
        "query": "Yoyogi Park Tokyo",
        "lat": 35.6717,
        "lng": 139.6950,
    },
    "nogi": {
        "name": "Nogi Shrine",
        "query": "Nogi Shrine Minato Tokyo",
        "lat": 35.6690,
        "lng": 139.7335,
    },
    "sannenzaka": {
        "name": "Sannenzaka / Ninenzaka",
        "query": "Sannenzaka Kyoto",
        "lat": 34.9980,
        "lng": 135.7820,
    },
    "higashiyama": {
        "name": "Higashiyama",
        "query": "Higashiyama Kyoto",
        "lat": 34.9985,
        "lng": 135.7805,
    },
    "kitaguchi": {
        "name": "Kitaguchi Hongu Fuji Sengen Shrine",
        "query": "Kitaguchi Hongu Fuji Sengen Shrine Fujiyoshida",
        "lat": 35.4705,
        "lng": 138.7955,
    },
    "chureito_street": {
        "name": "Fujiyoshida retro shopping street",
        "query": "Honcho-dori Fujiyoshida",
        "lat": 35.4875,
        "lng": 138.7950,
    },
    "shitennoji": {
        "name": "Shitenno-ji",
        "query": "Shitennoji Temple Osaka",
        "lat": 34.6539,
        "lng": 135.5164,
    },
    "kasuga": {
        "name": "Kasuga-taisha",
        "query": "Kasuga Taisha Nara",
        "lat": 34.6814,
        "lng": 135.8483,
    },
    "kuromon": {
        "name": "Kuromon Market",
        "query": "Kuromon Market Osaka",
        "lat": 34.6660,
        "lng": 135.5063,
    },
    "daigoji": {
        "name": "Daigo-ji",
        "query": "Daigo-ji Temple Kyoto",
        "lat": 34.9514,
        "lng": 135.8197,
    },
    "kyoto_station": {
        "name": "Kyoto Station",
        "query": "Kyoto Station",
        "lat": 34.9858,
        "lng": 135.7588,
    },
    "nara_park": {
        "name": "Nara Park",
        "query": "Nara Park",
        "lat": 34.6851,
        "lng": 135.8430,
    },
    "meiji": {
        "name": "Meiji Jingu",
        "query": "Meiji Jingu Shrine Tokyo",
        "lat": 35.6764,
        "lng": 139.6993,
    },
    "shibuya": {
        "name": "Shibuya Crossing",
        "query": "Shibuya Crossing Tokyo",
        "lat": 35.6595,
        "lng": 139.7005,
    },
    "shinjuku_gyoen": {
        "name": "Shinjuku Gyoen",
        "query": "Shinjuku Gyoen National Garden",
        "lat": 35.6852,
        "lng": 139.7100,
    },
    "jingu_gaien": {
        "name": "Jingu Gaien Ginkgo Avenue",
        "query": "Jingu Gaien Ginkgo Avenue Tokyo",
        "lat": 35.6785,
        "lng": 139.7175,
    },
    "harajuku": {
        "name": "Harajuku / Omotesando",
        "query": "Harajuku Station Tokyo",
        "lat": 35.6702,
        "lng": 139.7026,
    },
    "oishi": {
        "name": "Oishi Park",
        "query": "Oishi Park Kawaguchiko",
        "lat": 35.5095,
        "lng": 138.7518,
    },
    "kawaguchiko_town": {
        "name": "Kawaguchiko town",
        "query": "Kawaguchiko Station area",
        "lat": 35.4982,
        "lng": 138.7685,
    },
    "shinjuku": {
        "name": "Shinjuku",
        "query": "Shinjuku Station Tokyo",
        "lat": 35.6896,
        "lng": 139.7006,
    },
    "godzilla": {
        "name": "Godzilla Head Shinjuku",
        "query": "Godzilla Head Hotel Gracery Shinjuku",
        "lat": 35.6955,
        "lng": 139.7020,
    },
    "omoide": {
        "name": "Omoide Yokocho",
        "query": "Omoide Yokocho Shinjuku",
        "lat": 35.6933,
        "lng": 139.6995,
    },
    "dotonbori": {
        "name": "Dotonbori",
        "query": "Dotonbori Osaka",
        "lat": 34.6687,
        "lng": 135.5013,
    },
    "universal": {
        "name": "Universal Studios Japan",
        "query": "Universal Studios Japan Osaka",
        "lat": 34.6654,
        "lng": 135.4323,
    },
    "disney_sea": {
        "name": "Tokyo DisneySea",
        "query": "Tokyo DisneySea",
        "lat": 35.6267,
        "lng": 139.8851,
    },
    "abeno": {
        "name": "Abeno Harukas",
        "query": "Abeno Harukas Osaka",
        "lat": 34.6456,
        "lng": 135.5136,
    },
    "tennoji": {
        "name": "Tennoji Park",
        "query": "Tennoji Park Osaka",
        "lat": 34.6500,
        "lng": 135.5100,
    },
    "shinsekai": {
        "name": "Shinsekai",
        "query": "Shinsekai Osaka",
        "lat": 34.6524,
        "lng": 135.5063,
    },
    "yasaka": {
        "name": "Yasaka Pagoda / Hokan-ji",
        "query": "Hokan-ji Yasaka Pagoda Kyoto",
        "lat": 34.9985,
        "lng": 135.7790,
    },
    "haneda": {
        "name": "Haneda Airport",
        "query": "Haneda Airport Tokyo",
        "lat": 35.5494,
        "lng": 139.7798,
    },
    "hyatt_lax": {
        "name": "Hyatt Place LAX / Century Blvd",
        "query": "Hyatt Place LAX/Century Blvd 5959 West Century Blvd",
        "lat": 33.9456,
        "lng": -118.3860,
    },
    "lax": {
        "name": "Los Angeles International Airport",
        "query": "LAX Airport Tom Bradley International Terminal",
        "lat": 33.9416,
        "lng": -118.4085,
    },
    "mde": {
        "name": "Aeropuerto José María Córdova",
        "query": "Jose Maria Cordova Airport Medellin",
        "lat": 6.1645,
        "lng": -75.4231,
    },
    "daikoku": {
        "name": "Daikoku PA",
        "query": "Daikoku Parking Area Yokohama",
        "lat": 35.4545,
        "lng": 139.6805,
    },
    "akihabara_pickup": {
        "name": "Akihabara (recogida Daikoku)",
        "query": "Akihabara Station Tokyo",
        "lat": 35.6984,
        "lng": 139.7731,
    },
    "aomi_north": {
        "name": "Aomi North Temporary Parking",
        "query": "1-chome-2-8 Aomi, Koto City, Tokyo",
        "lat": 35.6252,
        "lng": 139.7784,
    },
}


def place(key: str) -> dict:
    p = PLACES[key]
    return {"name": p["name"], "query": p["query"], "lat": p["lat"], "lng": p["lng"]}


def participants(going_ids: list[str] | None = None, missing_reasons: dict | None = None) -> list:
    going_ids = going_ids if going_ids is not None else ALL_IDS
    missing_reasons = missing_reasons or {}
    out = []
    for t in TRAVELERS:
        going = t["id"] in going_ids
        item = {"id": t["id"], "name": t["name"], "going": going}
        if not going:
            item["reason"] = missing_reasons.get(t["id"], "No participa en este evento")
        out.append(item)
    return out


def all_except(*ids: str, reason: str) -> list:
    going = [i for i in ALL_IDS if i not in ids]
    return participants(going, {i: reason for i in ids})


def only(*ids: str, others_reason: str) -> list:
    return participants(list(ids), {i: others_reason for i in ALL_IDS if i not in ids})


def cost_jpy(amount: float, label: str = "Entrada") -> list:
    return [{"item": label, "amount": amount, "currency": "JPY", "perPerson": True}]


def slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9áéíóúñü]+", "-", s)
    return s.strip("-")[:48]


def parse_excel_rows() -> list[dict]:
    with zipfile.ZipFile(EXCEL) as z:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        shared = []
        for si in root:
            texts = [t.text or "" for t in si.iter(NS + "t")]
            shared.append("".join(texts))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        for s in wb.find(NS + "sheets"):
            if s.attrib.get("name") != "JP Trip":
                continue
            target = "xl/" + rid[s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]].lstrip("/")
            if target.startswith("xl/xl/"):
                target = target[3:]
            sheet = ET.fromstring(z.read(target))
            base = datetime(1899, 12, 30)

            def excel_time(v):
                try:
                    f = float(v)
                except Exception:
                    return None, None
                if f > 40000:
                    return (base + timedelta(days=int(f))).strftime("%Y-%m-%d"), None
                mins = int(round(f * 24 * 60))
                return None, f"{mins // 60:02d}:{mins % 60:02d}"

            rows = []
            for row in sheet.find(NS + "sheetData"):
                cells = {}
                for c in row:
                    ref = c.attrib.get("r", "")
                    col = "".join(ch for ch in ref if ch.isalpha())
                    t = c.attrib.get("t")
                    v = c.find(NS + "v")
                    isel = c.find(NS + "is")
                    val = ""
                    if t == "s" and v is not None and v.text:
                        val = shared[int(v.text)]
                    elif isel is not None:
                        val = "".join(x.text or "" for x in isel.iter(NS + "t"))
                    elif v is not None and v.text:
                        val = v.text
                    cells[col] = val
                if not str(cells.get("A", "")).startswith("Día"):
                    continue
                fecha, _ = excel_time(cells["E"]) if cells.get("E") else (None, None)
                _, hora = excel_time(cells["G"]) if cells.get("G") else (None, None)
                _, fin = excel_time(cells["H"]) if cells.get("H") else (None, None)
                if not fecha:
                    continue
                cost = None
                try:
                    cost = float(cells.get("J") or 0)
                except Exception:
                    cost = 0
                currency = cells.get("I") or "JPY"
                if currency == "COP" and cost:
                    cost_jpy_val = round(cost / JPY_TO_COP)
                elif currency == "JPY":
                    cost_jpy_val = cost
                else:
                    cost_jpy_val = cost
                rows.append(
                    {
                        "dayLabel": cells.get("A"),
                        "weekday": cells.get("B"),
                        "category": cells.get("C"),
                        "city": cells.get("D"),
                        "date": fecha,
                        "title": (cells.get("F") or "").strip(),
                        "start": hora,
                        "end": fin,
                        "currency": currency,
                        "cost": cost,
                        "costJPY": cost_jpy_val,
                        "note": cells.get("N") or "",
                        "addr": cells.get("O") or "",
                    }
                )
            return rows
    return []


WALK_IN_KEYS = (
    "park",
    "calle",
    "caminata",
    "barrio",
    "mercado",
    "nakamise",
    "ameyoko",
    "yanaka",
    "dotonbori",
    "higashiyama",
    "shinsekai",
    "harajuki",
    "harajuku",
    "shibuya",
    "omotesando",
    "gion",
    "punto",
    "explora",
    "actividad libre",
    "transporte publico",
    "transporte hotel",
    "transporte del hotel",
    "transporte interno",
    "bajada",
    "descenso",
    "envio",
    "recoger",
)


def guess_booking(title: str, category: str) -> tuple[str, str]:
    t = title.lower()
    if category == "Hotel":
        ready_hotels = ("establishment", "fujiyoshida", "osaka", "nipponbashi")
        if any(k in t for k in ready_hotels):
            return "ready", "Reservado y pagado según Excel (verde)"
        if "kioto" in t or "kyoto" in t or "kanazawa" in t or "yoyogi" in t:
            return "needs_reservation", "Dirección en Excel; confirmar si ya está pagado"
        return "needs_reservation", "Confirmar reserva de hotel"
    if "fuji-excursion" in t or "fuji excursion" in t:
        return "ready", "8/8 asientos: E90632 + reserva Sebastián · Kinshicho 07:07"
    if "biovortex" in t or "teamlabs" in t or "teamlab" in t:
        return "ready", "8 entradas Biovortex compradas, 14:30"
    if "kabuki" in t:
        return "needs_ticket", "Opcional: comprar el 31 oct o en taquilla"
    if "disney" in t:
        return "needs_ticket", "Decisión pendiente; no hay tickets"
    if "onsen" in t or "yurari" in t:
        return "walk_in", "Pago en sitio; no admite tatuajes"
    if "shinkansen" in t or "limited express" in t:
        return "needs_reservation", "Johan reserva los Shinkansen"
    if "bus estación kawaguchiko" in t or "bus kawaguchiko" in t:
        return "needs_reservation", "Reservar en Fujiyama Connect (~¥2.500)"
    if "ropeway" in t or "teleferico" in t or "teleférico" in t:
        return "walk_in", "Sin reserva: comprar ida y vuelta en taquilla (adulto ¥1.200 desde 1 nov 2026)"
    if any(k in t for k in ("templo", "santuario", "castillo", "pagoda", "museo", "jardín", "jardin", "torre", "harukas", "skytree")):
        if "senso" in t or "nezu" in t or "meiji" in t or "yasaka" in t or "palacio" in t:
            return "walk_in", "Entrada gratuita o donación"
        return "needs_ticket", "Entrada en taquilla el mismo día"
    if any(k in t for k in WALK_IN_KEYS):
        return "walk_in", "Sin reserva previa"
    if category == "Transporte":
        return "walk_in", "Suica / pago en sitio"
    if category == "Alimentacion":
        return "na", "Presupuesto estimado del Excel"
    return "walk_in", "Sin reserva previa"


def guess_place(title: str, city: str, note: str, addr: str) -> dict | None:
    t = title.lower()
    # Non-places: don't invent a Google query from the Excel row title
    if any(
        k in t
        for k in (
            "transporte publico",
            "transporte a ",
            "envio de maletas",
            "envío de maletas",
            "actividad libre",
            "dia comodin",
            "día comodín",
            "exploracion",
            "exploración",
        )
    ):
        return None

    mapping = [
        ("establishment", "establishment_asakusa"),
        ("senso", "sensoji"),
        ("skytree", "skytree"),
        ("ueno", "ueno"),
        ("museo nacional", "tokyo_museum"),
        ("ameyoko", "ameyoko"),
        ("nakamise", "sensoji"),
        ("nezu", "nezu"),
        ("yanaka", "yanaka"),
        ("ikebukuro", "ikebukuro"),
        ("palacio", "imperial"),
        ("kabuki", "kabukiza"),
        ("pokemon", "pokemon_center"),
        ("akihabara", "akihabara"),
        ("tsukiji", "tsukiji"),
        ("odaiba", "odaiba"),
        ("roppongi", "roppongi"),
        ("torre tokyo", "tokyo_tower"),
        ("torre de tokio", "tokyo_tower"),
        ("fuji-excursion", "kinshicho"),
        ("ropeway", "ropeway"),
        ("yurari", "yurari"),
        ("fujiyoshida airbnb", "fujiyoshida_airbnb"),
        ("chureito", "chureito"),
        ("mishima", "mishima"),
        ("hotel en kioto", "kyoto_hotel"),
        ("bambú", "arashiyama"),
        ("bambu", "arashiyama"),
        ("tenryu", "tenryuji"),
        ("otagi", "otagi"),
        ("kinkaku", "kinkakuji"),
        ("nijō", "nijo"),
        ("nijo", "nijo"),
        ("pontocho", "pontocho"),
        ("kiyomizu", "kiyomizu"),
        ("gion", "gion"),
        ("hōkan", "yasaka"),
        ("hokan", "yasaka"),
        ("yasaka", "yasaka"),
        ("nipponbashi", "osaka_airbnb"),
        ("osaka - airbnb", "osaka_airbnb"),
        ("tōdai", "nara"),
        ("todai", "nara"),
        ("nara", "nara"),
        ("fushimi", "fushimi"),
        ("biovortex", "biovortex"),
        ("kanazawa - airbnb", "kanazawa_airbnb"),
        ("kenroku", "kenrokuen"),
        ("hotel yoyogi", "yoyogi_hotel"),
        ("yoyogi uehara", "yoyogi_hotel"),
        ("parque yoyogi", "yoyogi_park"),
        ("yoyogi park", "yoyogi_park"),
        ("yoyogi", "yoyogi_park"),  # after hotel-specific keys
        ("meiji", "meiji"),
        ("nogi", "nogi"),
        ("ginkgo", "jingu_gaien"),
        ("jingu gaien", "jingu_gaien"),
        ("jingū gaien", "jingu_gaien"),
        ("harajuk", "harajuku"),
        ("omotesand", "harajuku"),
        ("oishi", "oishi"),
        ("kitaguchi", "kitaguchi"),
        ("fuji sengen", "kitaguchi"),
        ("calle comercial retro", "chureito_street"),
        ("sannenzaka", "sannenzaka"),
        ("ninenzaka", "sannenzaka"),
        ("higashiyama", "higashiyama"),
        ("shitenn", "shitennoji"),
        ("kasuga", "kasuga"),
        ("kuromon", "kuromon"),
        ("daigo", "daigoji"),
        ("ramen koji", "kyoto_station"),
        ("parque nara", "nara_park"),
        ("venados", "nara_park"),
        ("kawaguchiko", "kawaguchiko_town"),
        ("fujikawaguchiko", "kawaguchiko_town"),
        ("shibuya", "shibuya"),
        ("shinjuku gyoen", "shinjuku_gyoen"),
        ("godzilla", "godzilla"),
        ("omoide", "omoide"),
        ("shinjuku", "shinjuku"),
        ("dotonbori", "dotonbori"),
        ("hozenji", "dotonbori"),
        ("universal", "universal"),
        ("disney", "disney_sea"),
        ("harukas", "abeno"),
        ("tennoji", "tennoji"),
        ("tennōji", "tennoji"),
        ("shinsekai", "shinsekai"),
        ("daikoku", "daikoku"),
        ("nipponbashi", "osaka_airbnb"),
        ("den den", "osaka_airbnb"),
    ]
    for key, pid in mapping:
        if key in t:
            return place(pid)
    if note and re.match(r"^-?\d+\.\d+,-?\d+\.\d+", note.replace(" ", "")):
        parts = note.replace(" ", "").split(",")
        try:
            return {"name": title, "query": addr or title, "lat": float(parts[0]), "lng": float(parts[1])}
        except Exception:
            pass
    if addr and len(addr.strip()) > 8:
        return {"name": title, "query": addr.strip(), "lat": None, "lng": None}

    # Last resort: short clean English-ish city hint, not the full Excel blurb
    city_hint = {
        "Tokio v1": "Tokyo",
        "Tokio v2": "Tokyo",
        "Mt. fuji": "Kawaguchiko",
        "Kansai (Kioto": "Kyoto",
        "Kanazawa": "Kanazawa",
    }
    city_q = "Tokyo"
    for prefix, label in city_hint.items():
        if (city or "").startswith(prefix) or prefix in (city or ""):
            city_q = label
            break
    # Strip parenthetical Excel notes
    clean = re.sub(r"\([^)]*\)", " ", title)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) > 60:
        clean = clean[:60].rsplit(" ", 1)[0]
    return {"name": title, "query": f"{clean}, {city_q}, Japan", "lat": None, "lng": None}


def bring_for(title: str, category: str) -> tuple[list, list]:
    t = title.lower()
    # Daily basics live once at day level. Events only carry exceptions.
    bring = []
    dont = []
    if "onsen" in t:
        bring = ["Toalla pequeña", "Cambio de ropa", "Efectivo"]
        dont = ["Tatuajes visibles (Yurari no admite)", "Teléfono en el agua", "Toalla grande del hotel si no se permite"]
    if "templo" in t or "santuario" in t or "pagoda" in t:
        bring += ["Ropa cómoda que cubra hombros", "Monedas para ofrenda"]
        dont += ["Sombrero dentro del santuario", "Fotos donde esté prohibido"]
    if "shinkansen" in t or "tren" in t or "fuji-excursion" in t:
        bring += ["Reserva impresa o en el teléfono", "Snack ligero"]
        dont += ["Maleta grande si ya la enviaste con Yamato"]
    if "vuelo" in t or category == "vuelo":
        bring = ["Pasaporte", "QR Visit Japan Web", "eSIM Ubigi", "Cargador"]
        dont = ["Líquidos >100 ml en carry-on", "Más de 2 power banks"]
    if "mercado" in t or "tsukiji" in t:
        bring += ["Apetito temprano", "Efectivo"]
        dont += ["Tocar comida sin permiso"]
    if "akihabara" in t or "den den" in t:
        bring += ["Presupuesto claro para compras"]
        dont += ["Bloquear pasillos en arcades"]
    return bring[:5], dont[:4]


DAY_ESSENTIALS = {
    "bring": ["Suica cargada", "Teléfono con mapas offline", "Efectivo en yenes"],
    "avoid": ["Hablar fuerte en transporte público", "Comer caminando en zonas saturadas"],
}

GENERIC_EVENT_BRING = set(DAY_ESSENTIALS["bring"])
GENERIC_EVENT_AVOID = set(DAY_ESSENTIALS["avoid"])


def description_for(title: str, category: str, start: str | None, end: str | None) -> str:
    """Useful on-site plan. Route details are rendered separately from event metadata."""
    t = title.lower()
    plans = [
        (("envio de maletas", "envío de maletas"), "Entregar las maletas grandes en el mostrador de Yamato y conservar el comprobante. Verificar nombre, alojamiento o punto de recogida y fecha de entrega antes de salir."),
        (("recoger maletas",), "Presentar el comprobante de Yamato, comprobar que estén todas las piezas y revisar daños antes de abandonar el punto de recogida."),
        (("taxi desde onsen",), "Pedir uno o más taxis según la capacidad indicada. Confirmar el alojamiento en el mapa antes de subir y dividir el costo entre quienes ocupen cada vehículo."),
        (("bus a estacion kawaguchiko",), "Tomar el bus hacia Kawaguchiko Station y llegar con margen para el siguiente servicio. Si hay retraso, usar taxi."),
        (("bus estación kawaguchiko",), "Este es el enlace reservado hacia Mishima. Estar en la parada con el billete listo y no planear una conexión inmediata al bajar."),
        (("shinkansen mishima",), "Localizar el andén al llegar a Mishima y abordar con la reserva preparada. Comprar comida solo si queda margen real."),
        (("transporte interno en kioto",), "Llegar al alojamiento y dejar el equipaje. Este bloque absorbe la conexión desde la estación y cualquier demora del Shinkansen."),
        (("transporte hotel - arashiyama",), "Salir temprano hacia Arashiyama. Usar el tren como opción principal y conservar margen para caminar desde la estación."),
        (("taxi tenryu",), "Pedir el taxi al terminar Tenryu-ji y mostrar Otagi Nenbutsu-ji en el mapa. Confirmar que el conductor acepta llevar al grupo o dividirse."),
        (("bajada caminando",), "Elegir entre caminar cuesta abajo o tomar taxi según el cansancio. La hora de salida manda: Kinkaku-ji no debe quedar sin margen."),
        (("bus kinkaku",), "Tomar el bus hacia Nijō y bajar cerca del castillo. Si está saturado, dividir taxis para proteger la entrada al castillo."),
        (("transporte nijo-hotel",), "Volver directamente al hotel y descansar. No añadir una parada: este margen sostiene los baños y Pontocho."),
        (("transporte hotel - pontocho",), "Ir y volver desde el hotel en transporte público. Guardar la ubicación del alojamiento antes de salir de noche."),
        (("transporte hotel - kiyomizudera",), "Salir temprano y completar el último tramo a pie. Las calles finales tienen pendiente y pueden estar concurridas."),
        (("transporte kioto - osaka",), "Trasladarse a Osaka y comprobar el alojamiento antes de salir de la estación. Mantener juntos los comprobantes de equipaje Yamato."),
        (("transporte del hotel a estacion kintetsu-nara",), "Salir con margen hacia Kintetsu-Nara. Revisar el tren correcto y reagruparse antes de abandonar la estación."),
        (("transporte a osaka",), "Regresar a Osaka después de Kasuga-Taisha. Este traslado cierra la excursión; Dotonbori comienza solo después de llegar."),
        (("transporte osaka - fushimi",), "Hacer la ida temprano y conservar clara la ruta de regreso. El resto del día continúa en Kioto antes de volver a Osaka."),
        (("transporte fushimi-daigoji",), "Salir de Fushimi a la hora límite y enlazar metro/tren hacia Daigo-ji. No esperar a que todo el grupo alcance la cima."),
        (("transporte daigoji",), "Ir desde Daigo-ji hasta Kyoto Station. El almuerzo empieza al llegar; no sumar otra parada."),
        (("shinkansen osaka - nagoya",), "Abordar con la reserva lista y llevar solo mochila. Al llegar, guardar equipaje antes de la escala de Nagoya."),
        (("limited express shirasagi",), "Volver a la estación con margen, ubicar el andén y abordar con la reserva preparada. Llevar agua y algo ligero."),
        (("shinkansen kanazawa",), "Llegar temprano a Kanazawa Station y abordar con la reserva lista. Al llegar a Tokio, ir primero al alojamiento."),
        (("onsen", "yurari"), "Usar el baño como cierre prioritario del día. Confirmar reglas de tatuajes en la entrada, ducharse antes de entrar y acordar una hora de salida."),
        (("establishment asakusa",), "Llegar al Establishment, comprobar que todos tengan acceso y preparar la salida de la mañana siguiente."),
        (("hotel en fujiyoshida",), "Hacer check-in, cargar teléfonos y dejar lista la mochila. Confirmar la hora de salida hacia Chureito."),
        (("hotel en kioto",), "Llegar, hacer check-in y dejar preparada ropa cómoda para la salida temprana. Confirmar el regreso después de Pontocho."),
        (("hotel en osaka",), "Volver al alojamiento y preparar solo lo necesario para el día siguiente. Confirmar quién conserva la llave o código de acceso."),
        (("hotel en kanazawa",), "Llegar al alojamiento, comprobar el acceso y preparar la salida del día siguiente. Mantener el equipaje agrupado."),
        (("hotel tokyo 2",), "Volver al hotel de Yoyogi-Uehara y preparar la jornada siguiente. Confirmar la hora de salida y el trayecto al primer punto."),
        (("ueno park",), "Pasear por el eje central y el estanque sin intentar cubrir todo el parque. Salir a tiempo hacia el museo."),
        (("museo nacional",), "Priorizar la Galería Japonesa y una segunda colección de interés. Usar guardarropa si llevan compras o equipaje."),
        (("ameyoko",), "Recorrer la calle principal y sus pasajes laterales. Probar algo ligero; el almuerzo fuerte será en Nakamise."),
        (("nakamise",), "Recorrer los puestos hacia Senso-ji y almorzar aquí. Comprar y comer junto al puesto, no mientras caminan."),
        (("senso-ji",), "Entrar por Kaminarimon, seguir por Nakamise y terminar en el salón principal. Reagruparse junto a la gran linterna."),
        (("skytree",), "Subir solo si la visibilidad y la fila lo justifican. Si no, recorrer Solamachi y ver la torre desde la plaza."),
        (("nezu",), "Recorrer el santuario y el sendero de torii. Mantener la visita corta para conservar el horario de Yanaka."),
        (("yanaka",), "Bajar caminando por el barrio y almorzar en Yanaka Ginza. Reagruparse al final de la calle comercial."),
        (("sunshine city",), "Explorar Sunshine City y sus tiendas. Definir una hora y punto de encuentro antes de separarse."),
        (("halloween",), "Recorrer el ambiente de Halloween sin depender de un evento específico. Evitar calles saturadas y salir antes del cierre del transporte."),
        (("palacio imperial",), "Recorrer los jardines y miradores abiertos al público; no asumir acceso al interior del palacio."),
        (("kabuki",), "Actividad opcional. Consultar funciones de un solo acto y disponibilidad en taquilla antes de comprometer el resto de la tarde."),
        (("centro pokemon",), "Recorrer la tienda con un presupuesto y una hora de salida definidos. Las filas de caja pueden ser largas."),
        (("akihabara",), "Dividir el tiempo entre arcades, electrónica y tiendas de coleccionables. Acordar un punto fijo para reagruparse."),
        (("tsukiji",), "Desayunar temprano y recorrer el mercado exterior. Comprar y comer junto a cada puesto; salir puntuales hacia Odaiba."),
        (("odaiba",), "Pasear por el frente de la bahía y los miradores. Es el bloque recortable del día: salir a las 13:15 aunque falte algo."),
        (("ropeway", "teleferico", "teleférico"), "Comprar el billete de ida y vuelta en la taquilla; no requiere reserva. Subir, usar los miradores y bajar con margen para el siguiente bloque."),
        (("fujikawaguchiko",), "Almorzar y caminar cerca de la estación/lago. No alejarse si el bus turístico tiene poca frecuencia."),
        (("oishi",), "Parada opcional para ver el lago y el Fuji. Omitirla si hay cansancio, nubes o retraso; el onsen tiene prioridad."),
        (("chureito",), "Subir las escaleras con calma y usar el mirador de la pagoda. Salir antes de que la bajada comprometa el resto del día."),
        (("retro fujiyoshida",), "Bajar por la calle comercial y buscar las vistas del Fuji entre fachadas. Mantener libre la calzada para las fotos."),
        (("sengen",), "Recorrer el acceso, el gran torii y el santuario. Almorzar cerca antes de iniciar los traslados a Kioto."),
        (("bambú", "bambu"), "Entrar temprano, caminar el tramo principal y continuar hacia Tenryu-ji. No detener al grupo en medio del sendero."),
        (("tenryu",), "Priorizar el jardín y la vista desde la veranda. Salir a tiempo para el taxi a Otagi."),
        (("otagi",), "Recorrer los rakan de piedra y el recinto superior. Mantenerse en los senderos y respetar las zonas sin fotografía."),
        (("kinkaku",), "Seguir el circuito de sentido único alrededor del estanque. Almorzar cerca al terminar, sin alargar la visita."),
        (("castillo nij",), "Recorrer el palacio y sus jardines. Dar prioridad a los interiores antes del cierre y salir hacia el descanso del hotel."),
        (("baños publicos",), "Confirmar en la entrada las reglas sobre tatuajes y toallas. Ducharse antes del baño y no llevar el teléfono al agua."),
        (("pontocho",), "Caminar la calle y elegir un restaurante con disponibilidad. Definir presupuesto antes de entrar y volver juntos al hotel."),
        (("kiyomizu",), "Llegar temprano, recorrer la terraza y los pabellones. Empezar el descenso antes de que aumenten las multitudes."),
        (("sannenzaka", "ninenzaka"), "Bajar por las calles históricas con calma; los escalones pueden estar resbalosos. Evitar bloquear entradas y fachadas."),
        (("hōkan", "hokan"), "Ver la pagoda desde las calles autorizadas y continuar caminando. No depender de acceso interior."),
        (("higashiyama",), "Almorzar y recorrer las calles tradicionales. Mantener un punto de encuentro por si el grupo se separa."),
        (("gion",), "Caminar Hanami-koji, Shirakawa y Yasaka sin perseguir ni fotografiar de cerca a residentes o geiko."),
        (("kuromon",), "Desayunar en el mercado y comprar porciones pequeñas para compartir. Comer junto al puesto."),
        (("nipponbashi", "den den"), "Explorar tiendas de electrónica y cultura pop con un límite de compras. Reagruparse antes de seguir al templo."),
        (("shitenn",), "Recorrer el recinto principal y la pagoda. Mantener tono bajo y revisar restricciones de fotografía."),
        (("tennoji park",), "Cruzar el parque rumbo a Abeno Harukas; usar este bloque como descanso si el grupo va cansado."),
        (("harukas",), "Subir al mirador solo si la visibilidad es buena. Si la fila es larga, usar las áreas gratuitas del edificio."),
        (("shinsekai",), "Recorrer el barrio y cenar temprano. Dotonbori queda como extensión opcional solo si hay energía."),
        (("tōdai", "todai"), "Entrar al Gran Salón del Buda y recorrer el patio. Salir a la hora acordada hacia el parque."),
        (("venados", "sika"), "Caminar por el parque sin rodear ni provocar a los ciervos. Guardar comida y mapas para evitar que los muerdan."),
        (("kasuga",), "Seguir el sendero de linternas hasta el santuario y almorzar en la zona. Tomar el bus de regreso si el grupo va justo."),
        (("dotonbori", "hozenji"), "Recorrer el canal y terminar en Hozenji Yokocho. Elegir la cena antes de que las filas crezcan."),
        (("fushimi inari",), "Subir por los torii hasta Yotsutsuji; no es necesario alcanzar la cima. Dar la vuelta a la hora límite."),
        (("daigo-ji",), "Recorrer el recinto principal y la pagoda. Mantener la visita enfocada para llegar a Kyoto Ramen Koji."),
        (("ramen koji",), "Elegir el restaurante antes de hacer fila. Almorzar y fijar una hora de salida común."),
        (("exploracion", "exploración"), "Usar este bloque como margen real: café, estación de Kioto o descanso. No iniciar una visita lejana."),
        (("biovortex", "teamlab"), "Llegar con la entrada preparada y seguir el recorrido de la instalación. Llevar calzado cómodo y teléfono cargado."),
        (("comodin", "comodín", "universal"), "Elegir una sola opción para todo el día. Universal requiere entrada y planificación; Himeji/Kobe requiere horarios de tren; Osaka libre no requiere reserva."),
        (("día en nagoya", "dia en nagoya"), "Es una escala, no un día turístico completo. Guardar equipaje, almorzar cerca de la estación y volver con margen para el tren."),
        (("kenroku",), "Recorrer el circuito del estanque, Kotoji-tōrō y los pinos. Evitar intentar cubrir cada sendero."),
        (("higashi chaya",), "Caminar por las calles históricas y almorzar aquí. Entrar solo a locales abiertos al público."),
        (("casa de té", "casa de te"), "Elegir una casa que admita visitantes sin reserva. Seguir las indicaciones del anfitrión y mantener la visita breve."),
        (("katamachi",), "Pasear por el centro y usar el bloque como descanso/compras. Acordar dónde reagruparse."),
        (("nagamachi",), "Recorrer los canales, muros de barro y calles del antiguo barrio samurái sin entrar en propiedades privadas."),
        (("nomura",), "Visitar la residencia y su jardín. Guardar mochilas grandes y respetar el flujo por las habitaciones."),
        (("omicho",), "Almorzar en el mercado y recorrer los puestos de mariscos. Comer junto al local y evitar las horas más llenas."),
        (("oyama",), "Ver la puerta y recorrer el santuario. Es una visita corta antes del castillo."),
        (("castillo de kanazawa",), "Recorrer las puertas, murallas y jardines; entrar a interiores solo si el horario lo permite."),
        (("nocturno kanazawa",), "Paseo flexible por zonas iluminadas. Volver juntos y evitar añadir trayectos largos al final del día."),
        (("shinjuku gyoen",), "Recorrer un circuito corto por los jardines. Revisar la hora de cierre al entrar."),
        (("ayuntamiento",), "Subir al mirador gratuito si está abierto. Considerar controles de seguridad y posible fila."),
        (("godzilla",), "Caminar por Kabukicho y ver la cabeza de Godzilla desde la calle. Mantenerse en vías concurridas."),
        (("omoide",), "Elegir un local con espacio para el grupo o dividirse en mesas. Confirmar precios antes de pedir."),
        (("meiji",), "Entrar por el gran torii y recorrer el santuario. Por Shichi-Go-San habrá familias y más gente: observar con respeto."),
        (("parque yoyogi",), "Paseo y descanso después del santuario. Recortar este bloque si el día va retrasado."),
        (("harajuki", "harajuku", "omotesando"), "Recorrer Takeshita y continuar hacia Omotesando. Definir tiempo libre y punto de encuentro."),
        (("ginkgo",), "Caminar la avenida y el festival. Esperar mucha gente y conservar margen para Shibuya."),
        (("shibuya",), "Ver Hachiko, cruzar el scramble y recorrer las calles cercanas. Reagruparse junto a Hachiko."),
        (("nogi",), "Visitar el santuario y cenar en la zona. Última actividad: no añadir otra parada distante."),
        (("disney sea",), "Solo hacerlo si el grupo decide dedicarle el día completo y compra entradas. Si no, convertir el día en jornada libre real."),
        (("actividad libre",), "Bloque sin actividad cerrada. Elegir algo cercano al hotel o descansar; no asumir que todo el grupo hará lo mismo."),
    ]
    for keys, plan in plans:
        if any(key in t for key in keys):
            return plan

    if category.lower() == "hotel":
        return "Llegar al alojamiento, hacer check-in y preparar lo necesario para la mañana siguiente. Confirmar la hora de salida antes de dormir."
    if category.lower() == "transporte":
        return "Este bloque incluye el desplazamiento completo. Salir al inicio del horario indicado y seguir la ruta mostrada en la tarjeta."
    if category.lower() == "vuelo":
        return "Tener pasaporte y reserva a mano. Confirmar terminal y puerta en la aplicación de la aerolínea antes de salir."
    return "Recorrer el lugar dentro del horario indicado. Acordar un punto de encuentro y respetar la hora de salida."


def hotel_for_date(date: str) -> dict:
    if date <= "2026-11-02":
        # group at Establishment; Sergio/Arley Tobu from 1-2
        if date >= "2026-11-01":
            return {
                "name": "Tobu Levant (Sergio/Arley) · Establishment Asakusa (resto)",
                "group": "Establishment Asakusa (Oshiage)",
                "sergioArley": "Tobu Hotel Levant Tokyo (Kinshicho) — Booking 5449717587",
            }
        return {
            "name": "Establishment Asakusa (Oshiage)",
            "group": "Establishment Asakusa (Oshiage)",
            "sergioArley": "En tránsito / aún no en Tokio",
        }
    if date == "2026-11-03":
        return {
            "name": "Airbnb Fujiyoshida",
            "group": "Airbnb Fujiyoshida — código 23660346",
            "sergioArley": "Con el grupo",
        }
    if date in ("2026-11-04", "2026-11-05"):
        return {
            "name": "Hotel Kioto (Kariganecho)",
            "group": "Hotel Kioto (Kariganecho) — confirmar pago",
            "sergioArley": "Con el grupo",
        }
    if "2026-11-06" <= date <= "2026-11-10":
        return {
            "name": "Airbnb Osaka Nipponbashi",
            "group": "Airbnb Osaka Nipponbashi",
            "sergioArley": "Con el grupo",
        }
    if "2026-11-11" <= date <= "2026-11-13":
        return {
            "name": "Airbnb Kanazawa",
            "group": "Airbnb Kanazawa — confirmar pago",
            "sergioArley": "Con el grupo",
        }
    if "2026-11-14" <= date <= "2026-11-17":
        return {
            "name": "Hotel Yoyogi Uehara",
            "group": "Hotel Yoyogi Uehara — confirmar pago",
            "sergioArley": "Con el grupo",
        }
    return {"name": "Salida", "group": "Salida", "sergioArley": "Vuelo de regreso"}


CITY_CENTER = {
    "Tokio v1": place("establishment_asakusa"),
    "Mt. fuji": place("kawaguchiko"),
    "Kansai (Kioto": place("kyoto_hotel"),
    "Kanazawa": place("kanazawa_airbnb"),
    "Tokio v2": place("yoyogi_hotel"),
}


def participants_for_tokyo_v1(date: str, title: str) -> list:
    t = title.lower()
    # Sergio/Arley not in Tokyo until evening of Nov 1
    if date < "2026-11-01":
        return all_except("sergio", "arley", reason="Llegan a Narita el domingo 1 de noviembre por la tarde")
    if date == "2026-11-01":
        if any(k in t for k in ("palacio", "kabuki", "pokemon", "akihabara")):
            return all_except("sergio", "arley", reason="Aterrizan ~17:20–17:40; no alcanzan el plan diurno")
        if "hotel" in t and "establishment" in t:
            return all_except("sergio", "arley", reason="Duermen en Tobu Levant, Kinshicho")
    if date == "2026-11-02" and "daikoku" in t:
        return only("sergio", "arley", "pipe", "johan", others_reason="No van a Daikoku")
    # Pipe / Mafalda / Julián salen la noche del 16
    if date >= "2026-11-17":
        return all_except(
            "pipe",
            "mafalda",
            "julian",
            reason="Salen la noche del 16 de noviembre",
        )
    return participants()


def build_event_from_row(row: dict, idx: int) -> dict | None:
    title = row["title"]
    if not title:
        return None
    category_map = {
        "Hotel": "hotel",
        "Transporte": "transporte",
        "Entradas a sitios turisticos": "visita",
        "Alimentacion": "comida",
    }
    category = category_map.get(row["category"], "visita")
    # Skip generic meals as separate rich events — fold into day budget
    if category == "comida" and title in ("Desayuno", "Almuerzo", "Cena"):
        return None
    # Skip Excel placeholder "Transporte publico" — pollutes chain/map/buffers
    from audit_enrich import is_generic_transport, assign_track

    if is_generic_transport(title):
        return None

    booking_status, booking_detail = guess_booking(title, row["category"])
    to_place = guess_place(title, row["city"], row["note"], row["addr"])
    bring, dont = bring_for(title, category)

    inferred = False
    start, end = row["start"], row["end"]
    # Fix bogus madrugada times for Kyoto Nijo block (01:xx in excel)
    if start and start.startswith("01:") and row["date"] == "2026-11-05":
        start = {"01:20": "13:20", "01:50": "13:50"}.get(start, start)
        if end and end.startswith("0"):
            end = {"01:50": "13:50", "03:20": "15:20", "04:00": "16:00"}.get(end, end)
        inferred = True
    # Also remap orphan 03:xx / 04:xx starts on Nov 5
    if row["date"] == "2026-11-05" and start and (start.startswith("03:") or start.startswith("04:")):
        try:
            h, m = map(int, start.split(":"))
            start = f"{h + 12:02d}:{m:02d}"
            if end:
                eh, em = map(int, end.split(":"))
                if eh < 8:
                    end = f"{eh + 12:02d}:{em:02d}"
            inferred = True
        except ValueError:
            pass

    costs = []
    if row["costJPY"] and row["costJPY"] > 0 and category != "hotel":
        costs = cost_jpy(round(row["costJPY"]), "Costo estimado por persona (Excel)")
    elif category == "hotel" and row["costJPY"]:
        costs = [{"item": "Hotel (prorrateo Excel)", "amount": round(row["costJPY"]), "currency": "JPY", "perPerson": True}]

    travel = {"mode": "none", "durationMin": 0, "notes": ""}
    tl = title.lower()
    if "shinkansen" in tl:
        travel = {"mode": "tren", "durationMin": 120, "notes": "Shinkansen — reservar asiento"}
    elif "bus" in tl:
        travel = {"mode": "bus", "durationMin": 90, "notes": "Bus interurbano"}
    elif "taxi" in tl:
        travel = {"mode": "taxi", "durationMin": 20, "notes": "Taxi / Uber / GO"}
    elif "tren" in tl or "fuji-excursion" in tl:
        travel = {"mode": "tren", "durationMin": 150, "notes": "Tren reservado"}
    elif category == "visita":
        travel = {"mode": "walk", "durationMin": 15, "notes": "Caminata o trayecto corto desde el anterior"}

    parts = participants_for_tokyo_v1(row["date"], title)
    track = assign_track(row["date"], title, category, parts)
    eid = f"{row['date']}-{idx}-{slug(title)}"
    return {
        "id": eid,
        "start": start,
        "end": end,
        "inferred": inferred or (start is None and category == "visita"),
        "title": title,
        "category": category,
        "track": track,
        "endOfDay": category == "hotel",
        "flags": [],
        "description": description_for(title, category, start, end),
        "from": None,
        "to": to_place,
        "travel": travel,
        "participants": parts,
        "bookingStatus": booking_status,
        "bookingDetail": booking_detail,
        "costs": costs,
        "reservation": booking_detail if booking_status == "ready" else "",
        "image": "",
        "imageCredit": "",
        "bring": bring,
        "dontBring": dont,
        "source": "excel",
    }


def places_equal(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return False
    if a.get("lat") is not None and b.get("lat") is not None:
        if a["lat"] == b["lat"] and a.get("lng") == b.get("lng"):
            return True
    qa = (a.get("query") or a.get("name") or "").strip().lower()
    qb = (b.get("query") or b.get("name") or "").strip().lower()
    return bool(qa and qa == qb)


def has_coords(p: dict | None) -> bool:
    return bool(p and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lng"), (int, float)))


def haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    la1, lo1 = math.radians(a["lat"]), math.radians(a["lng"])
    la2, lo2 = math.radians(b["lat"]), math.radians(b["lng"])
    dla, dlo = la2 - la1, lo2 - lo1
    x = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def estimate_travel(frm: dict | None, to: dict | None, title: str, category: str, existing: dict | None) -> dict:
    """Realistic mode + duration from coordinates. Keeps flights / reserved trains."""
    t = (title or "").lower()
    existing = existing or {}

    if category == "vuelo" or existing.get("mode") == "flight" or "vuelo" in t:
        return existing if existing.get("mode") == "flight" else {
            "mode": "flight",
            "durationMin": existing.get("durationMin") or 0,
            "notes": existing.get("notes") or "Vuelo",
        }

    # Keep explicit reserved long-haul rails if already marked
    if any(k in t for k in ("shinkansen", "fuji-excursion", "fuji excursion", "limited express", "shirasagi")):
        if existing.get("durationMin") and existing.get("mode") in ("tren", "metro"):
            out = dict(existing)
            out["inferred"] = False
            return out

    if not has_coords(frm) or not has_coords(to):
        mode = existing.get("mode") or ("metro" if category in ("visita", "transporte") else "none")
        dur = existing.get("durationMin") or (30 if mode != "none" else 0)
        return {
            "mode": mode,
            "durationMin": dur,
            "notes": existing.get("notes") or "Sin coords — estimado genérico",
            "inferred": True,
        }

    km = haversine_km(frm, to)
    walk_min = int(km / 4.2 * 60) + 3  # ~4.2 km/h + buffer

    # Absurd jump (bad chain): don't pretend it's a 15-min walk
    if km > 80 and category != "vuelo":
        return {
            "mode": "tren",
            "durationMin": max(90, int(km / 2.5)),
            "notes": f"⚠ Origen/destino muy lejos (~{km:.0f} km). Revisar cadena del día.",
            "distanceKm": round(km, 1),
            "inferred": True,
        }

    if km <= 1.8:
        return {
            "mode": "walk",
            "durationMin": max(8, walk_min),
            "notes": f"Caminata ~{km:.1f} km",
            "distanceKm": round(km, 2),
            "inferred": True,
        }

    if km <= 9:
        # Metro/local: ~22 km/h effective + wait/transfer
        transit_min = max(18, int(km / 22 * 60) + 12)
        return {
            "mode": "metro",
            "durationMin": transit_min,
            "notes": f"Metro/tren local ~{km:.1f} km · a pie serían ~{walk_min} min",
            "distanceKm": round(km, 2),
            "walkDurationMin": walk_min,
            "inferred": True,
        }

    if km <= 50:
        transit_min = max(40, int(km / 40 * 60) + 15)
        return {
            "mode": "tren" if km > 15 else "metro",
            "durationMin": transit_min,
            "notes": f"Tren/bus ~{km:.1f} km · a pie ~{walk_min} min (no recomendado)",
            "distanceKm": round(km, 2),
            "walkDurationMin": walk_min,
            "inferred": True,
        }

    return {
        "mode": "tren",
        "durationMin": max(60, int(km / 60 * 60) + 20),
        "notes": f"Tramo largo ~{km:.0f} km",
        "distanceKm": round(km, 1),
        "inferred": True,
    }


def chain_from_to(events: list[dict], day_hotel_place: dict | None) -> None:
    """Set from = previous destination when it differs from this event's to.

    Never copy to → from. Ignore overseas/flight endpoints as chain anchors.
    Reject candidates >40 km away for local visits (use hotel instead).
    """
    prev = day_hotel_place
    for ev in events:
        if ev["category"] == "comida":
            continue
        if ev["from"] is None:
            candidate = prev
            if candidate and places_equal(candidate, ev.get("to")):
                candidate = None
            if (
                candidate
                and has_coords(candidate)
                and has_coords(ev.get("to"))
                and haversine_km(candidate, ev["to"]) > 40
                and ev.get("category") != "vuelo"
                and (ev.get("travel") or {}).get("mode") != "flight"
            ):
                candidate = None
            if (
                candidate is None
                and day_hotel_place
                and not places_equal(day_hotel_place, ev.get("to"))
            ):
                # Hotel only if it's in the same region as destination
                if (
                    has_coords(day_hotel_place)
                    and has_coords(ev.get("to"))
                    and haversine_km(day_hotel_place, ev["to"]) <= 40
                ):
                    candidate = day_hotel_place
                elif not has_coords(ev.get("to")):
                    candidate = day_hotel_place
            ev["from"] = candidate
        if places_equal(ev.get("from"), ev.get("to")):
            ev["from"] = None

        dest = ev.get("to")
        # Don't let flights / overseas points poison the local chain
        if ev.get("category") == "vuelo" or (ev.get("travel") or {}).get("mode") == "flight":
            continue
        if dest and (
            has_coords(dest)
            or (dest.get("query") and "transporte" not in (dest.get("name") or "").lower())
        ):
            if (
                day_hotel_place
                and has_coords(dest)
                and has_coords(day_hotel_place)
                and haversine_km(dest, day_hotel_place) > 200
            ):
                continue
            prev = dest


def apply_travel_estimates(events: list[dict]) -> None:
    for ev in events:
        if ev.get("category") == "comida":
            continue
        ev["travel"] = estimate_travel(
            ev.get("from"),
            ev.get("to"),
            ev.get("title") or "",
            ev.get("category") or "",
            ev.get("travel"),
        )


def shape_nov2(d: dict) -> None:
    """Split 2 Nov: Roppongi for everyone, Tower only for non-Daikoku, hotel returns as their own legs."""
    daikoku_ids = ("sergio", "arley", "pipe", "johan")
    tower_ids = ("julian", "mafalda", "tatiana", "sebastian")
    not_daikoku = "Van al tour Daikoku y no se suman a la Torre"
    not_tower = "Se quedan en Roppongi y siguen a la Torre; no van a Daikoku"

    def lock(ev: dict, start: str, end: str) -> None:
        ev["start"], ev["end"] = start, end
        ev["inferred"] = True
        ev["scheduleLocked"] = True

    for ev in d["events"]:
        t = ev["title"].lower()
        if "roppongi" in t:
            lock(ev, "14:00", "16:15")
            ev["track"] = "all"
            ev["optional"] = False
            ev["participants"] = participants()
            ev["from"] = place("odaiba")
            ev["to"] = place("roppongi")
            ev["description"] = (
                "Van los ocho. Salir de Odaiba a las 13:15: el metro a Roppongi son ~26 min y hace falta margen. "
                "A las 16:15 Sergio, Arley, Pipe y Johan se van a Aomi para el tour. "
                "Julián, Mafalda, Tati y Sebas se quedan y siguen a la Torre de Tokio. "
                "Cenar aquí solo si no van a Daikoku; los del tour comen algo corto y salen a tiempo."
            )
        elif "torre" in t:
            lock(ev, "16:55", "18:15")
            ev["track"] = "all"
            ev["optional"] = False
            ev["participants"] = only(*tower_ids, others_reason=not_daikoku)
            ev["from"] = place("roppongi")
            ev["to"] = place("tokyo_tower")
            ev["description"] = (
                "Solo Julián, Mafalda, Tati y Sebas. Sergio, Arley, Pipe y Johan no van: "
                "el tour Daikoku ya incluye una parada de fotos en la Torre y tienen que estar en Aomi a las 17:15. "
                "Salen de Roppongi a las 16:15. La caminata es ~1,5 km, unos 25 minutos, así que la visita empieza a las 16:55."
            )
        elif "establishment" in t:
            lock(ev, "22:40", "23:10")
            ev["endOfDay"] = True
            ev["track"] = "all"
            ev["participants"] = all_except(
                "sergio",
                "arley",
                reason="Duermen en el Tobu Levant, Kinshicho",
            )
            ev["from"] = place("establishment_asakusa")
            ev["to"] = place("establishment_asakusa")
            ev["description"] = (
                "Noche en el Establishment Asakusa. No es un trayecto: el desplazamiento está en los eventos de vuelta. "
                "Julián, Mafalda, Tati y Sebas llegan ~19:10 desde la Torre. "
                "Pipe y Johan llegan ~22:15 desde el tour."
            )

    d["events"].extend(
        [
            {
                "id": "2026-11-02-roppongi-aomi",
                "start": "16:15",
                "end": "17:15",
                "travelRole": "leg",
                "inferred": True,
                "scheduleLocked": True,
                "title": "Roppongi Hills → Aomi (salida del tour)",
                "category": "transporte",
                "track": "sergio_arley",
                "endOfDay": False,
                "flags": [],
                "description": (
                    "Solo Sergio, Arley, Pipe y Johan. Salir de Roppongi a las 16:15 para estar en "
                    "Aomi Norte (1-chome-2-8 Aomi) a las 17:15. Unos 40–50 min en metro "
                    "(Hibiya hasta Toyosu y Yurikamome, o taxi si van justo). "
                    "Los otros cuatro no hacen este tramo: siguen a la Torre."
                ),
                "from": place("roppongi"),
                "to": place("aomi_north"),
                "travel": {"mode": "metro", "durationMin": 45, "notes": "Roppongi → Aomi Norte"},
                "participants": only(*daikoku_ids, others_reason=not_tower),
                "bookingStatus": "na",
                "bookingDetail": "Trayecto al punto de encuentro GYGFWVYL2943",
                "costs": cost_jpy(400, "Metro (aprox.)"),
                "reservation": "",
                "image": "",
                "bring": ["Suica", "Confirmación del tour"],
                "dontBring": [],
                "source": "inferred",
            },
            {
                "id": "2026-11-02-torre-hotel",
                "start": "18:25",
                "end": "19:10",
                "travelRole": "leg",
                "inferred": True,
                "scheduleLocked": True,
                "title": "Torre de Tokio → Establishment Asakusa",
                "category": "transporte",
                "track": "all",
                "endOfDay": False,
                "flags": [],
                "description": (
                    "Vuelta al hotel del grupo que fue a la Torre: Julián, Mafalda, Tati y Sebas. "
                    "Salen de la Torre a las 18:25 (10 min para bajar y llegar al metro). "
                    "Unos 35 min hasta Asakusa / Oshiage, en el hotel ~19:10. "
                    "Sergio, Arley, Pipe y Johan no van en este trayecto."
                ),
                "from": place("tokyo_tower"),
                "to": place("establishment_asakusa"),
                "travel": {"mode": "metro", "durationMin": 35, "notes": "Torre de Tokio → Oshiage / Asakusa"},
                "participants": only(*tower_ids, others_reason=not_daikoku),
                "bookingStatus": "na",
                "bookingDetail": "Vuelta al hotel",
                "costs": cost_jpy(350, "Metro (aprox.)"),
                "reservation": "",
                "image": "",
                "bring": ["Suica"],
                "dontBring": [],
                "source": "inferred",
            },
            {
                "id": "2026-11-02-tour-tobu",
                "start": "21:30",
                "end": "22:20",
                "travelRole": "leg",
                "inferred": True,
                "scheduleLocked": True,
                "title": "Fin del tour → Tobu Levant",
                "category": "transporte",
                "track": "sergio_arley",
                "endOfDay": False,
                "flags": [],
                "description": (
                    "Sergio y Arley. Si Tokyo Turismo los deja en el Tobu (pedirlo por WhatsApp al +81 90 8383 5525), "
                    "este tramo ya va incluido. Si el fin sigue siendo Shibuya (2-chome-19-6), "
                    "son unos 45 min hasta Kinshicho. No es la vuelta al Establishment."
                ),
                "from": place("shibuya"),
                "to": place("tobu_levant"),
                "travel": {"mode": "metro", "durationMin": 45, "notes": "Shibuya → Kinshicho, si no los dejan en el hotel"},
                "participants": only("sergio", "arley", others_reason="No duermen en el Tobu"),
                "bookingStatus": "na",
                "bookingDetail": "Pedir dejada en el Tobu Levant al confirmar con el proveedor",
                "costs": [],
                "reservation": "GYGFWVYL2943",
                "image": "",
                "bring": ["Suica por si el tour termina en Shibuya"],
                "dontBring": [],
                "source": "inferred",
            },
            {
                "id": "2026-11-02-tour-establishment",
                "start": "21:30",
                "end": "22:20",
                "travelRole": "leg",
                "inferred": True,
                "scheduleLocked": True,
                "title": "Fin del tour → Establishment Asakusa",
                "category": "transporte",
                "track": "sergio_arley",
                "endOfDay": False,
                "flags": [],
                "description": (
                    "Pipe y Johan, al terminar el tour. Mismo hotel que el resto del grupo. "
                    "Pedir al proveedor dejada en Oshiage / Establishment. "
                    "Si terminan en Shibuya, unos 40 min en metro. Sergio y Arley van al Tobu, no en este trayecto."
                ),
                "from": place("shibuya"),
                "to": place("establishment_asakusa"),
                "travel": {"mode": "metro", "durationMin": 40, "notes": "Shibuya → Oshiage, si no los dejan en el hotel"},
                "participants": only("pipe", "johan", others_reason="Otro hotel o no van al tour"),
                "bookingStatus": "na",
                "bookingDetail": "Vuelta al Establishment después de Daikoku",
                "costs": [],
                "reservation": "",
                "image": "",
                "bring": ["Suica por si el tour termina en Shibuya"],
                "dontBring": [],
                "source": "inferred",
            },
            {
                "id": "2026-11-02-noche-tobu",
                "start": "22:25",
                "end": "22:45",
                "inferred": True,
                "scheduleLocked": True,
                "endOfDay": True,
                "title": "Noche en Tobu Levant",
                "category": "hotel",
                "track": "sergio_arley",
                "flags": [],
                "description": (
                    "Sergio y Arley duermen aquí, no en el Establishment. "
                    "Mañana: Yamato ~05:45 y Fuji Excursion 07:07 en Kinshicho."
                ),
                "from": place("tobu_levant"),
                "to": place("tobu_levant"),
                "travel": {"mode": "none", "durationMin": 0, "notes": ""},
                "participants": only("sergio", "arley", others_reason="Duermen en el Establishment Asakusa"),
                "bookingStatus": "ready",
                "bookingDetail": "Tobu Booking 5449717587",
                "costs": [],
                "reservation": "5449717587",
                "image": "",
                "bring": [],
                "dontBring": [],
                "source": "inferred",
            },
        ]
    )


def inject_special_events(days: dict) -> None:
    # Oct 30 — Sergio/Arley flights
    if "2026-10-30" in days:
        d = days["2026-10-30"]
        d["events"].insert(
            0,
            {
                "id": "2026-10-30-sergio-arley-mde-lax",
                "start": "14:10",
                "end": "22:50",
                "inferred": False,
                "title": "Vuelo Medellín → Los Ángeles (Sergio y Arley)",
                "category": "vuelo",
                "description": "AV370 MDE 14:10 → SAL 15:50, luego AV528 SAL 18:15 → LAX 22:50. Reserva AZU9U3, asientos 4A/4B. En el avión llenar Visit Japan Web y guardar los QR. Al salir, shuttle Hyatt Place LAX (piso 2, Hotel Shuttles).",
                "from": place("mde"),
                "to": place("lax"),
                "travel": {"mode": "flight", "durationMin": 520, "notes": "Escala en San Salvador"},
                "participants": only("sergio", "arley", others_reason="Ya están en Tokio con el grupo"),
                "bookingStatus": "ready",
                "bookingDetail": "AZU9U3 LifeMiles — confirmar aceptación del cambio de regreso",
                "costs": [],
                "reservation": "AZU9U3",
                "image": "",
                "bring": ["Pasaporte", "Confirmación AZU9U3", "Tarjeta para Hyatt"],
                "dontBring": ["Olvidar Visit Japan Web"],
                "source": "gmail",
            },
        )
        d["events"].append(
            {
                "id": "2026-10-30-hyatt",
                "start": "23:15",
                "end": "23:45",
                "inferred": True,
                "title": "Check-in Hyatt Place LAX",
                "category": "hotel",
                "description": "Hyatt Place LAX/Century Blvd, 5959 West Century Blvd. Check-in desde las 16:00; llegan ~22:50. Shuttle desde LAX. Desayuno incluido. Reserva Falabella 352754352300. Sin cancelación.",
                "from": place("lax"),
                "to": place("hyatt_lax"),
                "travel": {"mode": "bus", "durationMin": 20, "notes": "Hotel shuttle Hyatt Place LAX"},
                "participants": only("sergio", "arley", others_reason="En Tokio"),
                "bookingStatus": "ready",
                "bookingDetail": "Falabella 352754352300 — sin cambios ni cancelación",
                "costs": [],
                "reservation": "352754352300",
                "image": "",
                "bring": ["Voucher Falabella", "Documento"],
                "dontBring": ["Tomar shuttle del Hyatt Regency"],
                "source": "gmail",
            }
        )

    if "2026-10-31" in days:
        d = days["2026-10-31"]
        d["events"].insert(
            0,
            {
                "id": "2026-10-31-sq11",
                "start": "13:45",
                "end": "17:40",
                "inferred": False,
                "title": "Vuelo LAX → Narita SQ 11 (Sergio y Arley)",
                "category": "vuelo",
                "description": "Salir del Hyatt ~10:00 (checkout 11:00). Shuttle a Tom Bradley/Terminal B. SQ 11 reserva FOLZ4L. E-ticket 13:45/17:40; la app mostró 13:25/17:20 — confirmar en Manage Booking. Activar eSIM Ubigi en el vuelo. Llegan el 1 de noviembre.",
                "from": place("lax"),
                "to": place("narita_t1"),
                "travel": {"mode": "flight", "durationMin": 715, "notes": "Singapore Airlines, Economy W"},
                "participants": only("sergio", "arley", others_reason="En Tokio (Halloween Ikebukuro)"),
                "bookingStatus": "ready",
                "bookingDetail": "FOLZ4L — tiquetes 618 2479169347 / 9348",
                "costs": [],
                "reservation": "FOLZ4L",
                "image": "",
                "bring": ["Pasaporte", "QR Visit Japan", "eSIM Ubigi"],
                "dontBring": [],
                "source": "gmail",
            },
        )

    if "2026-11-01" in days:
        d = days["2026-11-01"]
        d["summary"] = (
            "El grupo hace Palacio Imperial, Kabuki opcional, Centro Pokémon y Akihabara. "
            "Sergio y Arley aterrizan en Narita ~17:20–17:40, van al Tobu Levant en Kinshicho y, si pueden, Senso-ji de noche. Sin Daikoku este día."
        )
        d["events"].extend(
            [
                {
                    "id": "2026-11-01-arrival",
                    "start": "17:40",
                    "end": "20:30",
                    "inferred": True,
                    "title": "Llegada Narita → Tobu Levant (Sergio y Arley)",
                    "category": "transporte",
                    "description": "Inmigración y maletas en Narita T1. Keisei Access Express a Oshiage (~46 min, ~¥1.170). Hanzomon dos paradas a Kinshicho. Check-in Tobu desde las 15:00 (pidieron 19:00–20:00; recepción hasta 00:00). Booking 5449717587. Opcional: Yamato en aeropuerto si ya tienen el nombre de la reserva.",
                    "from": place("narita_t1"),
                    "to": place("tobu_levant"),
                    "travel": {"mode": "tren", "durationMin": 70, "notes": "Keisei Access Express + Hanzomon"},
                    "participants": only("sergio", "arley", others_reason="Ya están en el plan diurno del grupo"),
                    "bookingStatus": "ready",
                    "bookingDetail": "Tobu Booking 5449717587 — ¥65.700",
                    "costs": cost_jpy(1170, "Access Express (aprox.)"),
                    "reservation": "5449717587",
                    "image": "",
                    "bring": ["Pasaporte", "Confirmación Tobu", "Suica o efectivo para tren"],
                    "dontBring": ["Cruzar la ciudad a Akihabara recién llegados"],
                    "source": "inferred",
                },
                {
                    "id": "2026-11-01-sensoji-night",
                    "start": "20:45",
                    "end": "21:45",
                    "inferred": True,
                    "title": "Senso-ji de noche (opcional — Sergio y Arley)",
                    "category": "visita",
                    "description": "Solo si quedan fuerzas. A ~10 minutos del Tobu. El salón principal cierra por la tarde: es Nakamise y el templo iluminado. Skytree solo si alcanzan última entrada; si no, dejarlo para el lunes.",
                    "from": place("tobu_levant"),
                    "to": place("sensoji"),
                    "travel": {"mode": "walk", "durationMin": 12, "notes": "Caminata o metro corto"},
                    "participants": only("sergio", "arley", others_reason="El grupo ya lo visitó el viernes"),
                    "bookingStatus": "walk_in",
                    "bookingDetail": "Sin reserva — exterior de noche",
                    "costs": [],
                    "reservation": "",
                    "image": "",
                    "bring": ["Abrigo", "Teléfono"],
                "dontBring": ["Maletas"],
                "source": "inferred",
            },
            ]
        )
        # Infer daytime schedule for the group track (before Sergio/Arley land)
        day_slots_01 = [
            ("transporte publico", "09:00", "09:45"),
            ("palacio", "10:00", "12:00"),
            ("kabuki", "12:30", "14:30"),
            ("pokemon", "15:00", "16:15"),
            ("akihabara", "16:30", "18:30"),
        ]
        for ev in d["events"]:
            t = ev["title"].lower()
            for key, start, end in day_slots_01:
                if key in t and not ev.get("start"):
                    ev["start"], ev["end"] = start, end
                    ev["inferred"] = True
                    break
        d["mapCenter"] = place("tobu_levant")

    if "2026-11-02" in days:
        d = days["2026-11-02"]
        d["summary"] = (
            "Los ocho: Tsukiji, Odaiba si da, y Roppongi Hills hasta las 16:15. "
            "Ahí se parte el grupo. Sergio, Arley, Pipe y Johan salen a Aomi (17:15) para el tour JDM; no van a la Torre. "
            "Julián, Mafalda, Tati y Sebas siguen de Roppongi a la Torre y vuelven al Establishment. "
            "El regreso al hotel es un trayecto aparte: Tobu Levant para Sergio y Arley; Establishment para Pipe y Johan al terminar el tour."
        )
        d["events"].append(
            {
                "id": "2026-11-02-daikoku",
                "start": "17:30",
                "end": "21:30",
                "inferred": False,
                "scheduleLocked": True,
                "title": "Tour JDM Fast & Furious — Daikoku",
                "category": "visita",
                "description": (
                    "Van Sergio, Arley, Pipe y Johan. GetYourGuide GYGFWVYL2943, guía en español, 4 horas, pagado 1.864.000 COP. "
                    "Llegar 17:15 al aparcamiento temporal Aomi Norte (1-chome-2-8 Aomi, Koto). "
                    "Ruta: Autobacs Shinonome (30 min) → Daikoku ~1 h → Torre de Tokio solo fotos (20 min). Shibuya es opcional: saltarlo. "
                    "El correo deja el fin en 2-chome-19-6 Shibuya, pero el regreso al hotel en zona céntrica está incluido: "
                    "escribir a Tokyo Turismo (+81 90 8383 5525) y pedir que los dejen en el Tobu Levant, Kinshicho. "
                    "Eso cierra el sueño antes del Fuji Excursion de las 07:07. Cancela con reembolso antes de las 17:30 del 1 de noviembre."
                ),
                "from": place("aomi_north"),
                "to": place("daikoku"),
                "travelInside": True,
                "travel": {
                    "mode": "car",
                    "durationMin": 50,
                    "notes": "El coche sale de Aomi. Esos minutos van dentro del tour, no antes.",
                },
                "participants": only(
                    "sergio",
                    "arley",
                    "pipe",
                    "johan",
                    others_reason="No van al tour Daikoku",
                ),
                "bookingStatus": "ready",
                "bookingDetail": "GYGFWVYL2943 · PIN GFeH9PTF · Tokyo Turismo +81 90 8383 5525 · llegar 17:15 Aomi Norte",
                "costs": [
                    {
                        "item": "Tour JDM Fast & Furious (pagado)",
                        "amount": 466000,
                        "currency": "COP",
                        "perPerson": True,
                    }
                ],
                "reservation": "GYGFWVYL2943",
                "image": "",
                "bring": ["Pasaporte o cédula", "PIN GFeH9PTF en la app GetYourGuide", "Teléfono cargado", "Abrigo"],
                "dontBring": ["Maleta", "Sumarse a la Torre de Tokio: ya va una parada de fotos en el tour"],
                "source": "gmail",
            }
        )
        day_slots_02 = [
            ("tsukiji", "08:00", "10:30"),
            ("odaiba", "11:30", "13:15"),
            ("roppongi", "14:00", "16:15"),
            ("torre tokyo", "16:45", "18:15"),
            ("transporte publico", "07:30", "08:00"),
        ]
        for ev in d["events"]:
            t = ev["title"].lower()
            for key, start, end in day_slots_02:
                if key in t and not ev.get("start"):
                    ev["start"], ev["end"] = start, end
                    ev["inferred"] = True
                    break
        shape_nov2(d)
        d["mapCenter"] = place("tobu_levant")

    if "2026-11-03" in days:
        d = days["2026-11-03"]
        d["summary"] = (
            "Fuji Excursion E90632 sale 07:07 desde Kinshicho (llegada Kawaguchiko 09:28). "
            "Ropeway, pueblo, onsen Yurari. Oishi es prescindible si hay cansancio post-Daikoku. "
            "Antes: enviar maletas a Osaka con Yamato."
        )
        for ev in d["events"]:
            t = ev["title"].lower()
            if "oishi" in t:
                ev["bookingDetail"] = "Prescindible — saltar si hay cansancio post-Daikoku"
                if "omitir" not in (ev.get("description") or ""):
                    ev["description"] = (ev.get("description") or "") + " Recomendación: omitir para llegar más temprano al onsen."
            if "envio de maletas" in t or "envío de maletas" in t:
                ev["start"], ev["end"] = "05:45", "06:30"
                ev["inferred"] = True
                ev["description"] = (
                    "Dejar maletas grandes en un Yamato / counter de envío antes del tren. "
                    "Recogida en Osaka el 6 nov. Ir a Kawaguchiko y Kioto solo con mochila."
                )
                ev["bookingStatus"] = "needs_reservation"
                ev["bookingDetail"] = "Contratar Yamato TA-Q-BIN la noche del 2 o madrugada del 3"
            if "transporte publico 2" in t or "linea turistica" in t or "línea turística" in t:
                ev["start"], ev["end"] = "09:40", "10:30"
                ev["inferred"] = True
                ev["description"] = (
                    "Tras llegar a Kawaguchiko (09:28), usar la línea turística / bus local "
                    "para moverse entre ropeway, pueblo y onsen (pase 2 días del Excel)."
                )
            if "fuji-excursion" in t or "fuji excursion" in t:
                ev["start"] = "07:07"
                ev["end"] = "09:28"
                ev["inferred"] = False
                ev["from"] = place("kinshicho")
                ev["to"] = place("kawaguchiko")
                ev["bookingStatus"] = "ready"
                ev["bookingDetail"] = (
                    "E90632 (4) + segunda reserva Sebastián (4) — 8/8 confirmados · "
                    "carro 2, 8A/8B/9A/9B en E90632 · pickup 31212393070521258"
                )
                ev["reservation"] = "E90632 + reserva Sebastián (4)"
                ev["description"] = (
                    "Estar en Kinshicho antes de las 06:45. Fuji Excursion 3 sale 07:07, llega Kawaguchiko 09:28. "
                    "Antes: enviar maletas grandes a Osaka con Yamato. Ir solo con mochila. "
                    "Los ocho van: E90632 (Sergio) + las 4 plazas adicionales que cerró Sebastián."
                )

    if "2026-11-18" in days:
        d = days["2026-11-18"]
        d["events"] = [
            {
                "id": "2026-11-18-to-haneda",
                "start": "08:30",
                "end": "10:00",
                "inferred": True,
                "title": "Yoyogi → Haneda (Sergio y Arley)",
                "category": "transporte",
                "description": "Salir del hotel ~08:30. Haneda ~45 min. Check-in JAL/Alaska.",
                "from": place("yoyogi_hotel"),
                "to": place("haneda"),
                "travel": {"mode": "tren", "durationMin": 45, "notes": "Monorail / Keikyu"},
                "participants": only("sergio", "arley", "tatiana", "johan", others_reason="Pipe, Julián y Mafalda salen la noche del 16"),
                "bookingStatus": "na",
                "bookingDetail": "Transporte al aeropuerto",
                "costs": cost_jpy(800, "Tren a Haneda (aprox.)"),
                "reservation": "",
                "image": "",
                "bring": ["Pasaporte", "Confirmación Alaska/JAL"],
                "dontBring": [],
                "source": "inferred",
            },
            {
                "id": "2026-11-18-alaska",
                "start": "12:45",
                "end": "11:55",
                "inferred": False,
                "title": "Haneda → Osaka → Los Ángeles (Alaska/JAL)",
                "category": "vuelo",
                "description": "JL225/AS7481 HND 12:45→KIX 14:10, JL60/AS7318 KIX 17:50→LAX 11:55 (horario público JAL). Arley CUYKTV/F2RP4W; Sergio UXMLXS/EMIYMU (con Johan Vargas, Tati, Johan Bolívar). Pedir asientos a JAL. Esa noche AV521 LAX 23:00.",
                "from": place("haneda"),
                "to": place("lax"),
                "travel": {"mode": "flight", "durationMin": 700, "notes": "Escala Osaka Kansai"},
                "participants": only("sergio", "arley", "tatiana", "johan", others_reason="Otra ruta de salida"),
                "bookingStatus": "ready",
                "bookingDetail": "CUYKTV / UXMLXS — confirmar horarios en portal",
                "costs": [],
                "reservation": "CUYKTV / UXMLXS",
                "image": "",
                "bring": ["Pasaporte", "Códigos JAL F2RP4W / EMIYMU"],
                "dontBring": [],
                "source": "gmail",
            },
        ]


def day_title(date: str, weekday: str, city: str, day_label: str) -> str:
    names = {
        "jueves": "Jueves",
        "viernes": "Viernes",
        "sábado": "Sábado",
        "sabado": "Sábado",
        "domingo": "Domingo",
        "lunes": "Lunes",
        "martes": "Martes",
        "miércoles": "Miércoles",
        "miercoles": "Miércoles",
    }
    w = names.get((weekday or "").lower(), weekday or "")
    city_clean = (city or "").rstrip("(").strip()
    return f"{w} {date} — {city_clean} ({day_label})"


def infer_remaining_times(events: list[dict]) -> None:
    """Deprecated wrapper — use audit_enrich.infer_times_by_track."""
    from audit_enrich import infer_times_by_track

    infer_times_by_track(events)


def hotel_place_for_day(date: str, day: dict):
    if date >= "2026-11-01" and date <= "2026-11-02":
        return place("tobu_levant")
    if date < "2026-11-01":
        return place("establishment_asakusa")
    return day.get("mapCenter")


def main():
    rows = parse_excel_rows()
    days: dict[str, dict] = {}

    for i, row in enumerate(rows):
        date = row["date"]
        if date not in days:
            city = row["city"]
            days[date] = {
                "date": date,
                "dayLabel": row["dayLabel"],
                "weekday": row["weekday"],
                "title": day_title(date, row["weekday"], city, row["dayLabel"]),
                "city": city,
                "summary": f"Plan del grupo en {city}. Detalle hora a hora abajo.",
                "mapCenter": CITY_CENTER.get(city, place("establishment_asakusa")),
                "hotel": hotel_for_date(date),
                "events": [],
                "foodBudgetJPY": 0,
                "dayFlags": [],
            }
        if row["category"] == "Alimentacion" and row["title"] in ("Desayuno", "Almuerzo", "Cena"):
            days[date]["foodBudgetJPY"] += row["costJPY"] or 0
            continue
        ev = build_event_from_row(row, i)
        if ev:
            days[date]["events"].append(ev)

    inject_special_events(days)

    # Stamp track/flags on injected events before enrichment
    from audit_enrich import assign_track, enrich_days, write_audit_json

    for date, d in days.items():
        for ev in d["events"]:
            ev.setdefault("flags", [])
            if "track" not in ev:
                ev["track"] = assign_track(
                    date, ev.get("title") or "", ev.get("category") or "", ev.get("participants")
                )
            if ev.get("category") == "hotel":
                ev["endOfDay"] = True

    day_list = [days[date] for date in sorted(days.keys())]

    audit = enrich_days(day_list, chain_from_to, apply_travel_estimates, hotel_place_for_day)

    for d in day_list:
        d["dayEssentials"] = {
            "bring": list(DAY_ESSENTIALS["bring"]),
            "avoid": list(DAY_ESSENTIALS["avoid"]),
        }
        total = d["foodBudgetJPY"]
        for e in d["events"]:
            e["bring"] = [
                item for item in (e.get("bring") or []) if item not in GENERIC_EVENT_BRING
            ]
            e["dontBring"] = [
                item for item in (e.get("dontBring") or []) if item not in GENERIC_EVENT_AVOID
            ]
            for c in e.get("costs") or []:
                if c.get("perPerson") and c.get("currency") == "JPY":
                    total += c.get("amount") or 0
        d["perPersonTotalJPY"] = round(total)
        d["perPersonTotalCOP"] = round(total * JPY_TO_COP)
        d["exchangeRateJPYCOP"] = JPY_TO_COP
        if d.get("hotel") and not d["hotel"].get("name"):
            d["hotel"]["name"] = d["hotel"].get("group") or "Hotel"

    apply_images(day_list)

    payload = {
        "meta": {
            "title": "Itinerario Japón 2026 — Akihabara Dream",
            "subtitle": "Grupo de 8 · 29 oct – 18 nov 2026",
            "startDate": day_list[0]["date"] if day_list else "2026-10-29",
            "endDate": day_list[-1]["date"] if day_list else "2026-11-18",
            "fxJPY_to_COP": JPY_TO_COP,
            "travelers": TRAVELERS,
            "source": "Excel Sebastián + reservas Gmail + ajustes Sergio/Arley",
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "auditCounts": audit.get("counts"),
        },
        "days": day_list,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_path = OUT.parent / "audit.json"
    write_audit_json(audit, audit_path)
    print(f"Wrote {OUT} — {len(day_list)} days, {sum(len(d['events']) for d in day_list)} events")
    print(f"Wrote {audit_path} — flags {audit.get('counts')}")
    write_day_pages(day_list)
    print(f"Wrote {len(day_list)} day pages under dias/")


DAY_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex, nofollow" />
    <title>{title} · Viaje Japón</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Sans+JP:wght@500;700;800&display=swap"
      rel="stylesheet"
    />
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""
    />
    <link rel="stylesheet" href="../css/theme.css" />
  </head>
  <body data-date="{date}">
    <main class="wrap" id="day-root">
      <header class="day-hero">
        <a class="back" href="../index.html">← Índice</a>
        <p class="eyebrow" id="day-date" style="margin-top:1rem;"></p>
        <h1 id="day-title">{title}</h1>
        <p id="day-summary" style="color:var(--muted);max-width:40rem;"></p>
        <figure class="day-cover" id="day-cover" hidden>
          <img id="day-cover-image" src="" alt="" />
          <figcaption id="day-cover-caption"></figcaption>
        </figure>
        <div class="stats">
          <div class="stat"><div class="label">Ciudad</div><div class="value" id="stat-city">—</div></div>
          <div class="stat"><div class="label">Hotel</div><div class="value" id="stat-hotel">—</div></div>
          <div class="stat"><div class="label">Total / pers. (JPY)</div><div class="value" id="stat-jpy">—</div></div>
          <div class="stat"><div class="label">Total / pers. (COP)</div><div class="value" id="stat-cop">—</div></div>
        </div>
        <div class="maps-warn" id="maps-warn" hidden></div>
        <div id="day-map" aria-label="Mapa del día"></div>
      </header>

      <section class="events" id="events" aria-label="Eventos del día"></section>

      <footer class="site-footer">
        Abrí cada evento (tocá la fila ▾) para ver mapa, ruta, costos y qué llevar.
        · <a href="../auditoria.html">Informe de auditoría</a>
      </footer>
    </main>
    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script type="module" src="../js/day.js"></script>
  </body>
</html>
"""


def write_day_pages(day_list: list[dict]) -> None:
    dias = OUT.parent.parent / "dias"
    dias.mkdir(parents=True, exist_ok=True)
    for d in day_list:
        html = DAY_PAGE_TEMPLATE.format(date=d["date"], title=d["title"])
        (dias / f"{d['date']}.html").write_text(html, encoding="utf-8")


def apply_images(day_list: list[dict]) -> None:
    """Attach a local photo that matches the place, not a loose city keyword."""
    # First match wins. Specific places stay ahead of city or transport words.
    rules: list[tuple[tuple[str, ...], str]] = [
        (("halloween",), "halloween-ikebukuro.jpg"),
        (("senso-ji", "sensoji"), "sensoji.jpg"),
        (("skytree",), "skytree.jpg"),
        (("museo nacional",), "tokyo-museum.jpg"),
        (("ameyoko",), "ameyoko.jpg"),
        (("nakamise",), "nakamise.jpg"),
        (("ueno",), "ueno.jpg"),
        (("nezu",), "nezu.jpg"),
        (("yanaka",), "yanaka.jpg"),
        (("ikebukuro",), "ikebukuro.jpg"),
        (("palacio", "imperial"), "imperial-palace.jpg"),
        (("pokemon",), "pokemon-center.jpg"),
        (("kabuki",), "kabukiza.jpg"),
        (("akihabara",), "akihabara.jpg"),
        (("narita",), "narita.jpg"),
        (("medell",), "flight.jpg"),
        (("hyatt",), "hyatt.jpg"),
        (("tsukiji",), "tsukiji.jpg"),
        (("odaiba",), "odaiba.jpg"),
        (("aomi", "daikoku", "fast & furious", "jdm"), "daikoku.jpg"),
        (("roppongi",), "roppongi.jpg"),
        (("chureito",), "chureito.jpg"),
        (("hōkan", "hokan", "pagoda"), "yasaka-pagoda.jpg"),
        (("torre tokyo", "torre de tokio"), "tokyo-tower.jpg"),
        (("tobu",), "tobu-levant.jpg"),
        (("establishment",), "asakusa-hotel.jpg"),
        (("yamato", "maletas"), "yamato.jpg"),
        (("ropeway", "teleferico", "teleférico"), "fuji-ropeway.jpg"),
        (("oishi",), "oishi.jpg"),
        (("onsen", "yurari", "termales"), "onsen.jpg"),
        (("sengen",), "fuji-sengen.jpg"),
        (("retro",), "fujiyoshida.jpg"),
        (("hotel en fujiyoshida",), "kawaguchiko.jpg"),
        (("fuji-excursion", "fuji excursion"), "fuji-train.jpg"),
        (("shinkansen", "kioto - osaka", "transporte a osaka"), "shinkansen.jpg"),
        (("shirasagi", "limited express"), "shinkansen.jpg"),
        (("kasuga",), "kasuga.jpg"),
        (("linea turistica", "línea turística", "bus "), "bus.jpg"),
        (("kawaguchiko", "fujikawaguchiko"), "kawaguchiko.jpg"),
        (("arashiyama", "bambú", "bambu"), "arashiyama.jpg"),
        (("tenryu",), "tenryuji.jpg"),
        (("otagi",), "otagi.jpg"),
        (("kinkaku", "pabellon", "pabellón"), "kinkakuji.jpg"),
        (("nijō", "nijo"), "nijo.jpg"),
        (("pontocho",), "pontocho.jpg"),
        (("kiyomizu",), "kiyomizu.jpg"),
        (("sannenzaka", "ninenzaka"), "sannenzaka.jpg"),
        (("gion",), "gion.jpg"),
        (("higashiyama",), "higashiyama.jpg"),
        (("fushimi",), "fushimi.jpg"),
        (("daigo",), "daigoji.jpg"),
        (("ramen",), "ramen.jpg"),
        (("biovortex", "teamlab"), "teamlab.jpg"),
        (("baño", "bano"), "sento.jpg"),
        (("hotel en kioto", "hotel en kyoto"), "kyoto-hotel.jpg"),
        (("kuromon",), "kuromon.jpg"),
        (("nipponbashi", "den den"), "nipponbashi.jpg"),
        (("shitenn", "shitenno"), "shitennoji.jpg"),
        (("tennoji",), "tennoji.jpg"),
        (("harukas",), "harukas.jpg"),
        (("shinsekai",), "shinsekai.jpg"),
        (("dotonbori", "hozenji"), "dotonbori.jpg"),
        (("universal", "himeji", "comodin", "comodín"), "universal.jpg"),
        (("disney",), "disneysea.jpg"),
        (("tōdai", "todai"), "todaiji.jpg"),
        (("venados", "sika", "parque nara"), "nara-deer.jpg"),
        (("kasuga",), "kasuga.jpg"),
        (("nara",), "nara-deer.jpg"),
        (("kenroku",), "kenrokuen.jpg"),
        (("chaya",), "higashi-chaya.jpg"),
        (("casa de t",), "tea-house.jpg"),
        (("castillo de kanazawa",), "kanazawa-castle.jpg"),
        (("nagamachi",), "nagamachi.jpg"),
        (("nomura",), "nomura.jpg"),
        (("omicho",), "omicho.jpg"),
        (("oyama",), "oyama.jpg"),
        (("nocturno",), "kanazawa-night.jpg"),
        (("katamachi",), "kanazawa-stay.jpg"),
        (("hotel en kanazawa",), "kanazawa-stay.jpg"),
        (("kanazawa",), "kanazawa-stay.jpg"),
        (("gyoen",), "gyoen.jpg"),
        (("ayuntamiento",), "tmg.jpg"),
        (("godzilla",), "godzilla.jpg"),
        (("omoide",), "yokocho.jpg"),
        (("yoyogi uehara", "hotel tokyo 2"), "yoyogi-hotel.jpg"),
        (("meiji",), "meiji.jpg"),
        (("parque yoyogi",), "yoyogi-park.jpg"),
        (("harajuku", "harajuki", "omotesando"), "harajuku.jpg"),
        (("ginkgo", "jingu gaien"), "ginkgo.jpg"),
        (("shibuya", "hachiko"), "shibuya.jpg"),
        (("nogi",), "nogi.jpg"),
        (("haneda",), "haneda.jpg"),
        (("nagoya",), "nagoya.jpg"),
        (("hotel en osaka",), "osaka-stay.jpg"),
        (("actividad libre",), "tokyo-free.jpg"),
        (("exploracion", "exploración"), "higashiyama.jpg"),
        (("fujiyoshida",), "fujiyoshida.jpg"),
    ]
    for d in day_list:
        for ev in d.get("events") or []:
            t = (ev.get("title") or "").lower()
            cat = ev.get("category") or ""
            chosen = ""
            for keys, filename in rules:
                if any(k in t for k in keys):
                    chosen = filename
                    break
            if not chosen and cat == "vuelo":
                chosen = "flight.jpg"
            elif not chosen and cat == "hotel":
                chosen = "tokyo-free.jpg"
            elif not chosen and cat == "transporte":
                chosen = "metro.jpg"
            elif not chosen and cat == "visita":
                chosen = "tokyo-free.jpg"
            elif not chosen and cat == "comida":
                chosen = "kuromon.jpg"
            if chosen:
                ev["image"] = f"../img/{chosen}"
                ev["imageCredit"] = ""


if __name__ == "__main__":
    main()
