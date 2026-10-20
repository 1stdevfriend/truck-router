import { useRef, useState } from 'react'
import { fetchPlan } from './api'
import MapView from './MapView'
import TripForm from './TripForm'
import type { Plan, PlanRequest } from './types'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = useRef(0) // ignore responses from superseded requests

  async function runPlan(req: PlanRequest) {
    const id = ++latest.current
    setLoading(true)
    setError(null)
    try {
      const result = await fetchPlan(req)
      if (id === latest.current) setPlan(result)
    } catch (err) {
      if (id === latest.current) setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      if (id === latest.current) setLoading(false)
    }
  }

  const best = plan?.routes[plan.recommended]

  return (
    <>
      <main className="page">
        <header className="hero">
          <h1>Plan a safer route</h1>
          <p className="sub">Compare 3 truck routes by weather risk, load weight and travel time.</p>
        </header>

        <TripForm loading={loading} hasPlan={!!plan} onSubmit={runPlan} />

        <div aria-live="polite">
          {error && (
            <p className="alert error" role="alert">
              {error}
            </p>
          )}
          {plan && best && !error && (
            <section className="result">
              <h2>
                Recommended: {best.label} <span className="muted">({best.source})</span>
              </h2>
              <p>{plan.reason}</p>
              {plan.warnings.map((w) => (
                <p key={w} className="alert warn">
                  {w}
                </p>
              ))}
            </section>
          )}
        </div>
      </main>

      <section className="map-section" aria-label="Route map">
        <MapView />
      </section>
    </>
  )
}
