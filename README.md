# Viaje Japón — sitio del itinerario (grupo de 8)

Sitio estático en español con el plan del grupo (Excel de Sebastián), un índice por día y páginas diarias con eventos desplegables, participantes, costos, estado de reserva y mapas **Leaflet + OpenStreetMap** (sin API key).

## Abrir el sitio

Los módulos ES (`import`) y `fetch` del JSON requieren un origen HTTP (no `file://`).

Desde esta carpeta:

```bash
cd ~/Documents/viaje-japon/web
python3 -m http.server 8765
```

Abrí [http://localhost:8765/](http://localhost:8765/).

## Filtrar por persona

En el índice, tocá uno o más nombres (Sergio, Arley, …). Solo se listan los días donde esa(s) persona(s) tienen eventos. Al abrir un día, solo ves esos eventos; el filtro viaja en la URL (`?p=sergio,arley`).

- Tiles: Esri World Street Map vía Leaflet (etiquetas en alfabeto latino; sin API key).
- Ruta aproximada origen→destino: [OSRM](https://router.project-osrm.org/) (walking/driving).
- Link “Abrir ruta en Google Maps” usa nombres de lugar + `hl=es` (metro/tren en modo transit).
- No hace falta `config.js` ni API key de Google.

## Regenerar datos

```bash
python3 scripts/build_itinerary.py
```

Salida:

- `data/itinerary.json` — fuente única del contenido
- `dias/YYYY-MM-DD.html` — una página por día

## Estructura

```
web/
  index.html
  css/theme.css
  js/app.js day.js shared.js
  data/itinerary.json
  dias/*.html
  scripts/build_itinerary.py
  assets/events/
```

## Leyenda de badges

| Badge | Significado |
|---|---|
| Listo | Reserva/entrada ya comprada |
| Hay que reservar | Falta reservar con anticipación |
| Falta comprar entrada | Entrada aún no comprada |
| Sin reserva | Walk-in |
| Horario inferido | Hora estimada (no viene del Excel) |
| No todos van | Participantes parciales |

## Notas piloto

- **1 nov**: Sergio/Arley llegan a Narita; el grupo hace el plan diurno sin ellos. Sin Daikoku ese día.
- **2 nov noche**: Daikoku solo Sergio, Arley, Pipe y Johan.
- **3 nov**: Fuji Excursion E90632 sale 07:07 desde Kinshicho — buffer de sueño tras Daikoku.
