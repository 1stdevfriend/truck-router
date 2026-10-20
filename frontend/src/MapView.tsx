import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'

const STYLE_URL = 'https://tiles.openfreemap.org/styles/fiord' // navy basemap to match the page

// MapLibre throws without WebGL2 (old device, or hardware acceleration off);
// check first so the rest of the app stays usable.
const hasWebGL2 = () => !!document.createElement('canvas').getContext('webgl2')

export default function MapView() {
  const container = useRef<HTMLDivElement>(null)
  const [supported] = useState(hasWebGL2)

  useEffect(() => {
    if (!supported) return
    const map = new maplibregl.Map({
      container: container.current!,
      style: STYLE_URL,
      center: [-98.5, 39.8], // continental US
      zoom: 3.5,
    })
    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    return () => map.remove()
  }, [supported])

  return (
    <div ref={container} className="map">
      {!supported && (
        <p className="map-error" role="alert">
          The map needs WebGL, which this browser has turned off. Turn on hardware acceleration or try another browser.
        </p>
      )}
    </div>
  )
}
