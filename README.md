# Truck Router

Compare 3 truck routes between two US places by the weather risk a truck will meet along each one. The risk takes into account where the truck will be at each hour, and how heavy its load is.

**Live:** https://spotter-truck-routing.vercel.app · API: https://backend-production-60380.up.railway.app/api/health

## What it does

1. Enter an origin and a destination (US address autocomplete), a departure time, the load weight, and a checkpoint interval of 10, 25 or 50 mi.
2. The backend asks OpenRouteService for truck (HGV) routes. If ORS returns fewer than 3, it makes extra variant requests (avoid highways, avoid tolls, a detour via-point), drops duplicates and keeps the 3 most distinct routes.
3. Checkpoints are placed every N road-miles. Each one gets an ETA from the route's per-step driving times.
4. One batched Open-Meteo request fetches the hourly forecast for every checkpoint and the heatmap corridor. Each checkpoint is classified using the forecast hour its truck arrives in.
5. Routes are ranked and the best one is recommended, with the reason it won and warnings if needed.
6. The map shows the 3 routes, risk-coloured checkpoints (click one for details), summary cards linked to the map, and a risk heatmap with an hour slider (departure to +48 h).

## Risk rules

| Level | Wind (mph) | Rain (in/h) | Snow (in/h) |
|---|---|---|---|
| Low | < 25 | < 0.10 | < 0.5 |
| Moderate | 25–35 | 0.10–0.25 | 0.5–1.0 |
| High | 35–45 | 0.25–0.50 | 1.0–2.0 |
| Severe | 45–55 | 0.50–1.00 | 2.0–3.0 |
| No Travel | ≥ 55 | > 1.00 | > 3.0 |

- **Load rules (wind only):** above 40,000 lb, High becomes Severe. Above 30,000 lb, Severe becomes No Travel.
- **Checkpoint level:** the worst of wind (after the load rule), rain and snow.
- **Wind:** levels use the sustained 10 m wind speed. Gusts are shown but not scored.

**Interpretation notes**
- **Band edges:** the spec's bands overlap at the edges, so each band's lower bound is inclusive. For example, 0.25 in/h of rain is High.
- **Checkpoints:** they sit at mile 0, N, 2N, … and the destination. Each one covers half the gap to each neighbour, and its level counts for those miles.
- **Forecast hour:** wind uses the nearest forecast hour. Rain and snow use the hour bucket that contains the ETA, because Open-Meteo reports them as totals for the hour ending at each timestamp.
- **Ranking order:** fewest No-Travel miles, then fewest Severe miles, fewest High miles, lowest mile-weighted average risk (0–4), and finally shortest time. If every route has some No-Travel miles, the least bad one is recommended along with a "delay departure" warning.

## Stack

| | |
|---|---|
| Frontend | Vite, React, TypeScript, MapLibre GL (OpenFreeMap tiles) — deployed on Vercel |
| Backend | Python 3.12 (uv), Django 5, DRF, gunicorn — deployed on Railway |
| Data | OpenRouteService (geocoding + HGV directions, API key), Open-Meteo (forecasts, no key) |

The backend has no database. Forecasts are cached per 0.1° cell for 30 minutes, and address searches for 24 hours, in Django's in-memory cache.

```
backend/planner/
  ors.py        geocoding, HGV routes, variant fallback, picking distinct routes
  sampling.py   checkpoints every N miles + ETA
  weather.py    batched Open-Meteo fetch, cache, conditions at an ETA
  risk.py       threshold bands + load rules
  heatmap.py    corridor grid + [point][hour] risk matrix
  plan.py       puts it together: scoring, ranking, response
frontend/src/
  TripForm, PlaceInput   form + autocomplete
  MapView                routes, checkpoints, heatmap, slider
  RouteCards             per-route summary, linked to the map
```

## Run locally

You need [uv](https://docs.astral.sh/uv/), Node 20+, and a free [OpenRouteService key](https://openrouteservice.org/dev/#/signup).

```bash
cp .env.example .env          # set ORS_API_KEY; keep DJANGO_DEBUG=1
cd backend && uv run python manage.py runserver     # http://127.0.0.1:8000
cd frontend && npm install && npm run dev           # http://localhost:5173 (proxies /api to :8000)
```

Run the backend and frontend in separate terminals, starting each from the repo root.

Tests: `cd backend && uv run pytest`

## API

`GET /api/geocode?q=denver` → `{"results": [{"label", "lon", "lat"}]}`

`POST /api/plan`
```json
{"origin": {"lon": -87.63, "lat": 41.88}, "destination": {"lon": -104.99, "lat": 39.74},
 "departure": "2026-10-21T08:00:00-05:00", "weight_lb": 35000, "interval_mi": 25}
```
The response contains `recommended`, `ranking`, `reason`, `warnings`, and `routes[]`. Each route has its geometry, checkpoints with weather and level, `miles_by_level`, `avg_risk` and `max_risk`. The response also has `heatmap: {points: [[lon, lat]], risk: [[level per hour 0..48]]}`.

Errors come back as `400` with field messages (bad input), or `502` with `{"error": "..."}` (no route, routing or weather service down, departure beyond the 16-day forecast).

## Deploy

- **Backend (Railway):** run `cd backend && railway up --service backend --ci`. Set these environment variables: `ORS_API_KEY`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` (the Vercel URL). The start command is in `railpack.json`, and gunicorn uses a 120 s timeout from `gunicorn.conf.py`.
- **Frontend (Vercel):** run `cd frontend && vercel --prod --yes`, with `VITE_API_URL` set to the Railway URL.

## Limits

- **Forecast range:** departures are limited to 14 days ahead, so the whole trip fits inside Open-Meteo's 16-day forecast.
- **Route length:** ORS limits truck routes to about 3,700 mi.
- **Open-Meteo quota:** the free tier allows about 10,000 location-calls a day. Each plan uses a few hundred (checkpoints plus heatmap cells), and the per-cell cache is the only throttle.
- **Heatmap colours:** a heatmap blends nearby points, so its colours are approximate. Checkpoint levels are exact.
