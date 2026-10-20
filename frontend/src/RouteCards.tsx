import type { CSSProperties } from 'react'
import { formatDuration, formatTime, RISK_COLOR, RISK_LABEL, RISK_LEVELS, ROUTE_COLORS } from './display'
import type { Plan } from './types'

type Props = { plan: Plan; selected: number; onSelect: (id: number) => void }

/** One card per route, best first. Clicking a card selects that route on the map. */
export default function RouteCards({ plan, selected, onSelect }: Props) {
  return (
    <ol className="route-cards" aria-label="Routes, best first">
      {plan.ranking.map((i) => {
        const r = plan.routes[i]
        const levels = RISK_LEVELS.filter((l) => r.miles_by_level[l] > 0)
        return (
          <li key={r.id}>
            <button
              type="button"
              className="route-card"
              aria-pressed={r.id === selected}
              onClick={() => onSelect(r.id)}
              style={{ '--route': ROUTE_COLORS[r.id] } as CSSProperties}
            >
              <span className="card-head">
                <span className="swatch" aria-hidden="true" />
                <strong>{r.label}</strong>
                {r.id === plan.recommended && <span className="badge">Recommended</span>}
              </span>
              <span>
                {r.distance_mi} mi · {formatDuration(r.duration_h)} · arrives {formatTime(r.arrival)}
              </span>
              <span className="risk-bar" aria-hidden="true">
                {levels.map((l) => (
                  <span key={l} style={{ flex: r.miles_by_level[l], background: RISK_COLOR[l] }} />
                ))}
              </span>
              <span className="levels">{levels.map((l) => `${RISK_LABEL[l]} ${r.miles_by_level[l]} mi`).join(' · ')}</span>
              <span className="levels">
                Average risk {r.avg_risk} / 4 · Worst {RISK_LABEL[r.max_risk]}
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
