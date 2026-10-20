import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { formatTime, RISK_COLOR, RISK_LABEL, RISK_LEVELS, ROUTE_COLORS } from './display'
import type { Plan } from './types'

const STYLE_URL = 'https://tiles.openfreemap.org/styles/fiord' // navy basemap to match the page
const EMPTY = { type: 'FeatureCollection' as const, features: [] }
const HOURS = 48 // heatmap covers departure (hour 0) to +48 h

// Each heatmap point carries every hour's level as h0..h48; the slider only swaps which one is weighted.
const heatWeight = (hour: number) => ['/', ['get', `h${hour}`], 4] as maplibregl.ExpressionSpecification

// MapLibre throws without WebGL2 (old device, or hardware acceleration off);
// check first so the rest of the app stays usable.
const hasWebGL2 = () => !!document.createElement('canvas').getContext('webgl2')

type Props = { plan: Plan | null; selected: number; onSelect: (id: number) => void }

export default function MapView({ plan, selected, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popup = useRef(new maplibregl.Popup({ maxWidth: '240px' }))
  const [supported] = useState(hasWebGL2)
  const [ready, setReady] = useState(false)
  const [hour, setHour] = useState(0)
  // Map handlers are bound once; they read the current props through this ref.
  const latest = useRef({ plan, selected, onSelect })
  useEffect(() => {
    latest.current = { plan, selected, onSelect }
  })

  useEffect(() => {
    if (!supported) return
    const map = new maplibregl.Map({
      container: container.current!,
      style: STYLE_URL,
      center: [-98.5, 39.8], // continental US
      zoom: 3.5,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    map.on('load', () => {
      map.addSource('heat', { type: 'geojson', data: EMPTY })
      map.addSource('routes', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'heat',
        type: 'heatmap',
        source: 'heat',
        paint: {
          'heatmap-weight': heatWeight(0),
          // ~1.5x the 0.5-degree point spacing at every zoom, so cells blend without stacking up.
          'heatmap-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 9, 10, 1152],
          'heatmap-opacity': 0.6,
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(0, 0, 0, 0)',
            0.25,
            RISK_COLOR.moderate,
            0.5,
            RISK_COLOR.high,
            0.75,
            RISK_COLOR.severe,
            1,
            RISK_COLOR.no_travel,
          ],
        },
      })
      map.addSource('checkpoints', { type: 'geojson', data: EMPTY })
      map.addLayer({
        id: 'routes',
        type: 'line',
        source: 'routes',
        layout: { 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['get', 'z'] },
        paint: { 'line-color': ['get', 'color'], 'line-width': ['get', 'width'], 'line-opacity': ['get', 'opacity'] },
      })
      map.addLayer({
        id: 'checkpoints',
        type: 'circle',
        source: 'checkpoints',
        paint: {
          'circle-radius': 6,
          'circle-color': ['get', 'color'],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#0b1a2c',
        },
      })

      map.on('click', 'routes', (e) => {
        const id = e.features?.[0]?.properties.id
        if (typeof id === 'number') latest.current.onSelect(id)
      })
      map.on('click', 'checkpoints', (e) => {
        const { plan, selected } = latest.current
        const cp = plan?.routes[selected]?.checkpoints[e.features?.[0]?.properties.i]
        if (!cp) return
        // Every value here is a number or one of our own labels, so plain HTML is safe.
        popup.current
          .setLngLat([cp.lon, cp.lat])
          .setHTML(
            `<strong>${RISK_LABEL[cp.risk]}</strong> · mile ${cp.mile.toFixed(0)}<br>` +
              `ETA ${formatTime(cp.eta)}<br>` +
              `Wind ${cp.wind_mph.toFixed(0)} mph, gusts ${cp.gust_mph.toFixed(0)} mph<br>` +
              `Rain ${cp.rain_in_hr.toFixed(2)} in/h · Snow ${cp.snow_in_hr.toFixed(2)} in/h`,
          )
          .addTo(map)
      })
      for (const layer of ['routes', 'checkpoints']) {
        map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'))
        map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''))
      }
      setReady(true)
    })
    return () => {
      mapRef.current = null
      map.remove()
    }
  }, [supported])

  // Redraw routes and the selected route's checkpoints.
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const routes = plan?.routes ?? []
    ;(map.getSource('routes') as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: routes.map((r) => {
        const on = r.id === selected
        return {
          type: 'Feature',
          properties: { id: r.id, color: ROUTE_COLORS[r.id], width: on ? 6 : 3, opacity: on ? 1 : 0.5, z: on ? 1 : 0 },
          geometry: { type: 'LineString', coordinates: r.geometry },
        }
      }),
    })
    ;(map.getSource('checkpoints') as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: (routes[selected]?.checkpoints ?? []).map((cp, i) => ({
        type: 'Feature',
        properties: { i, color: RISK_COLOR[cp.risk] },
        geometry: { type: 'Point', coordinates: [cp.lon, cp.lat] },
      })),
    })
    popup.current.remove()
  }, [ready, plan, selected])

  // New plan: load its heatmap, rewind the slider and zoom to the routes (not on every selection change).
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map) return
    const heat = plan?.heatmap ?? { points: [], risk: [] }
    ;(map.getSource('heat') as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: heat.points.map((coordinates, i) => ({
        type: 'Feature',
        properties: Object.fromEntries(heat.risk[i].map((level, h) => [`h${h}`, level])),
        geometry: { type: 'Point', coordinates },
      })),
    })
    setHour(0)
    if (!plan) return
    const bounds = new maplibregl.LngLatBounds()
    for (const r of plan.routes) for (const c of r.geometry) bounds.extend(c)
    map.fitBounds(bounds, { padding: 48 })
  }, [ready, plan])

  useEffect(() => {
    if (ready) mapRef.current?.setPaintProperty('heat', 'heatmap-weight', heatWeight(hour))
  }, [ready, hour])

  const at = plan && formatTime(new Date(Date.parse(plan.departure) + hour * 3_600_000).toISOString())

  return (
    <div ref={container} className="map">
      {!supported && (
        <p className="map-error" role="alert">
          The map needs WebGL, which this browser has turned off. Turn on hardware acceleration or try another browser.
        </p>
      )}
      {plan && (
        <div className="map-panel">
          <label className="hour">
            <span>
              Weather risk at <strong>{at}</strong> (+{hour} h)
            </span>
            <input
              type="range"
              min={0}
              max={HOURS}
              value={hour}
              aria-valuetext={`${at}, ${hour} hours after departure`}
              onChange={(e) => setHour(Number(e.target.value))}
            />
          </label>
          <ul className="legend" aria-label="Risk colours">
            {RISK_LEVELS.map((l) => (
              <li key={l}>
                <span className="dot" style={{ background: RISK_COLOR[l] }} />
                {RISK_LABEL[l]}
              </li>
            ))}
          </ul>
          <p className="legend-note">Shading shows risk around the routes at that hour; no shading means Low.</p>
        </div>
      )}
    </div>
  )
}
