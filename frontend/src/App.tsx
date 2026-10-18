import { useEffect, useState } from 'react'
import MapView from './MapView'

type Health = { status: string; ors_configured: boolean }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setHealth)
      .catch(() => setError(true))
  }, [])

  const label = error
    ? 'API unreachable'
    : !health
      ? 'Checking API…'
      : health.ors_configured
        ? 'API ok'
        : 'API ok · ORS key missing'

  return (
    <>
      <MapView />
      <div className="status" role="status" data-ok={!!health && !error}>
        {label}
      </div>
    </>
  )
}
