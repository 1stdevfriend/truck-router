# Weather-Aware Truck Routing — Build Plan

## Decisions
| Area | Choice |
|---|---|
| Routing + geocoding | OpenRouteService, `driving-hgv` with load weight; if fewer than 3 routes come back, make variant requests (avoid highways/tollways, via-point detour), drop duplicates, keep the 3 most distinct |
| Weather | Open-Meteo (no key), hourly, batched coordinates |
| Wind | Classify on sustained 10 m wind; show gusts in the UI |
| Sampling | User picks 10 / 25 / 50 mi (default 25) |
| No Travel | Routes with No-Travel miles rank below all others; if every route has some, recommend the least bad and show a "delay departure" warning |
| Ranking | No-Travel miles → Severe miles → High miles → avg risk → duration |
| Heatmap | Composite risk on a grid around all routes, hours 0–48 from departure |
| Frontend | Vite + React + TypeScript + MapLibre GL (OpenFreeMap tiles) |
| Backend | Python 3.12 (uv), Django 5 + DRF, pytest |
| Hosting | Render, one service (Django serves the React build) |
| Git | Handled by the user |

## Checkpoints
Each one ends with a demo you can run. We don't move on until you approve it.

0. **Toolchain** — install uv + Python 3.12; get an ORS API key; create `.env`.
1. **Django boilerplate** — `backend/` with Django 5 + DRF, env-based settings, `/api/health`, pytest wired up.
2. **React boilerplate** — `frontend/` with Vite + TS, a full-screen MapLibre map, Vite proxy `/api` → Django, health check shown.
3. **Risk engine** — pure functions: wind/rain/snow bands, load rules, worst-of per checkpoint; boundary tests.
4. **ORS client** — geocode autocomplete endpoint, HGV directions with alternatives, variant fallback, dedupe → 3 routes.
5. **Checkpoint sampling + ETA** — points every N miles along each polyline, ETA from departure + interpolated ORS step durations; tests.
6. **Weather at ETA** — one batched Open-Meteo call per plan, pick the forecast hour for each checkpoint's ETA, classify it; cached.
7. **Scoring + `/api/plan`** — miles per risk level, avg risk, ranking, recommendation + warnings; tests on ranking.
8. **Trip form UI** — origin/destination autocomplete, departure datetime, weight, interval; loading/error states.
9. **Routes on map** — 3 colored routes, recommended one highlighted, risk-colored checkpoint markers with popups (ETA, wind/gust, rain, snow, level), summary cards synced with the map.
10. **Heatmap data** — corridor grid around the routes, one 0–48 h Open-Meteo fetch, compact risk matrix `[point][hour]`.
11. **Heatmap + slider UI** — MapLibre heatmap layer; the slider swaps data client-side (no refetch), plus a legend.
12. **Polish + README** — perf pass, edge cases (bad address, no route, forecast horizon), responsive layout, docs.
13. **Deploy to Render** — WhiteNoise + gunicorn, build script, env vars; smoke-test the live URL; Loom talking points.

## Open interpretation notes
- Band edges overlap in the PDF (e.g. rain 0.25 is listed as both Moderate and High). Rule: the lower bound is inclusive, so 0.25 → High.
- The load rules apply to wind only. A checkpoint's level is the worst of wind+load, rain and snow.
- Each checkpoint stands for the segment that ends at it, so its level counts for that segment's miles.
