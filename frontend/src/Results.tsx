import { useEffect, useRef } from 'react'
import { formatTime } from './display'
import MapView from './MapView'
import RouteCards from './RouteCards'
import type { Plan } from './types'

type Props = {
  plan: Plan
  title: string
  selected: number
  onSelect: (id: number) => void
  onClose: () => void
}

/** Full-screen results: route sheet beside the map. Esc or "Edit trip" goes back to the form. */
export default function Results({ plan, title, selected, onSelect, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    if (!ref.current?.open) ref.current?.showModal()
  }, [])

  const best = plan.routes[plan.recommended]

  return (
    <dialog ref={ref} className="results" aria-labelledby="results-title" onClose={onClose}>
      <aside className="sheet">
        <header className="sheet-head">
          <button type="button" className="back" onClick={() => ref.current?.close()}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15 5l-7 7 7 7" />
            </svg>
            Edit trip
          </button>
          <h2 id="results-title">{title}</h2>
          <p className="trip-meta">
            Departs {formatTime(plan.departure)} · {plan.weight_lb.toLocaleString()} lb · checkpoint every{' '}
            {plan.interval_mi} mi
          </p>
        </header>

        <section className="verdict" aria-label="Recommendation">
          <h3>
            Take {best.label} <span>({best.source})</span>
          </h3>
          <p>{plan.reason}</p>
          {plan.warnings.map((w) => (
            <p key={w} className="warning">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3l10 18H2z" />
                <path className="cut" d="M12 10v5M12 18v.01" />
              </svg>
              {w}
            </p>
          ))}
        </section>

        <RouteCards plan={plan} selected={selected} onSelect={onSelect} />
      </aside>

      <div className="map-pane">
        <MapView plan={plan} selected={selected} onSelect={onSelect} />
      </div>
    </dialog>
  )
}
