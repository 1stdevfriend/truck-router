import { useRef, useState } from 'react'
import { fetchPlan } from './api'
import Results from './Results'
import TripForm from './TripForm'
import TruckLoader from './TruckLoader'
import type { Plan, PlanRequest } from './types'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState(0)
  const [open, setOpen] = useState(false)
  const latest = useRef(0) // ignore responses from superseded requests

  async function runPlan(req: PlanRequest, tripTitle: string) {
    const id = ++latest.current
    setLoading(true)
    setError(null)
    setPlan(null) // don't show the previous trip while the new one loads
    setOpen(false)
    try {
      const result = await fetchPlan(req)
      if (id === latest.current) {
        setPlan(result)
        setTitle(tripTitle)
        setSelected(result.recommended)
        setOpen(true)
      }
    } catch (err) {
      if (id === latest.current) setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      if (id === latest.current) setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <svg className="logo" viewBox="0 0 64 64" aria-hidden="true">
          <rect x="11" y="11" width="42" height="42" rx="5" transform="rotate(45 32 32)" />
          <g>
            <rect x="16" y="25" width="18" height="12" rx="1.5" />
            <path d="M35.5 37V28.5h5.6l3.9 5V37z" />
            <circle cx="21.5" cy="39.5" r="2.8" />
            <circle cx="40" cy="39.5" r="2.8" />
          </g>
        </svg>
        Truck Route Weather
      </header>

      <main className="intro">
        <h1>Plan a safer route</h1>
        <p className="lede">
          Compare 3 truck routes by the weather your load will meet along each one, at the hour the truck gets there.
        </p>

        <TripForm loading={loading} hasPlan={!!plan} onSubmit={runPlan} />

        <div className="outcome" aria-live="polite">
          {error && (
            <p className="alert" role="alert">
              <strong>Couldn't plan this trip.</strong> {error}
            </p>
          )}
          {plan && !open && (
            <button type="button" className="reopen" onClick={() => setOpen(true)}>
              Show routes for {title}
            </button>
          )}
        </div>
      </main>

      {loading && <TruckLoader />}
      {plan && open && (
        <Results plan={plan} title={title} selected={selected} onSelect={setSelected} onClose={() => setOpen(false)} />
      )}
    </div>
  )
}
