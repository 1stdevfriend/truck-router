import type { CSSProperties } from 'react'
import { formatDuration, formatTime, RISK_COLOR, RISK_LABEL, RISK_LEVELS, ROUTE_COLORS } from './display'
import type { Plan } from './types'

type Props = { plan: Plan; selected: number; onSelect: (id: number) => void }

const miles = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 1 })

/** One option per route, best first. Choosing one selects that route on the map. */
export default function RouteCards({ plan, selected, onSelect }: Props) {
  return (
    <ol className="route-list" aria-label="Routes, best first">
      {plan.ranking.map((i, rank) => {
        const r = plan.routes[i]
        const levels = RISK_LEVELS.filter((l) => r.miles_by_level[l] > 0)
        return (
          <li key={r.id} style={{ '--i': rank } as CSSProperties}>
            <button
              type="button"
              className="route"
              aria-pressed={r.id === selected}
              onClick={() => onSelect(r.id)}
              style={{ '--route': ROUTE_COLORS[r.id] } as CSSProperties}
            >
              <span className="route-head">
                <span className="swatch" aria-hidden="true" />
                <strong>{r.label}</strong>
                <span className="source">{r.source}</span>
                {r.id === plan.recommended && <span className="badge">Recommended</span>}
              </span>

              <span className="stats">
                <span>
                  <b>{miles(r.distance_mi)} mi</b>
                  <small>Distance</small>
                </span>
                <span>
                  <b>{formatDuration(r.duration_h)}</b>
                  <small>Drive time</small>
                </span>
                <span>
                  <b>{formatTime(r.arrival)}</b>
                  <small>Arrives</small>
                </span>
              </span>

              <span className="risk-bar" aria-hidden="true">
                {levels.map((l) => (
                  <span key={l} style={{ flex: r.miles_by_level[l], background: RISK_COLOR[l] }} />
                ))}
              </span>
              <span className="levels">
                {levels.map((l) => (
                  <span key={l}>
                    <span className="dot" style={{ background: RISK_COLOR[l] }} aria-hidden="true" />
                    {RISK_LABEL[l]} <b>{miles(r.miles_by_level[l])} mi</b>
                  </span>
                ))}
              </span>
              <span className="summary">
                Worst <b>{RISK_LABEL[r.max_risk]}</b> · average risk <b>{r.avg_risk.toFixed(2)}</b> of 4
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
