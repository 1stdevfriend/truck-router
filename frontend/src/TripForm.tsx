import { useState } from 'react'
import PlaceInput from './PlaceInput'
import type { Interval, Place, PlanRequest } from './types'

type Props = {
  loading: boolean
  hasPlan: boolean
  onSubmit: (req: PlanRequest) => void
}

const INTERVALS: Interval[] = [10, 25, 50]
const MAX_DAYS_AHEAD = 14 // leaves room for the trip inside the 16-day forecast

/** Format a Date for <input type="datetime-local"> in the browser's time zone. */
function toLocalInput(d: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function nextHour() {
  const d = new Date()
  d.setHours(d.getHours() + 1, 0, 0, 0)
  return d
}

export default function TripForm({ loading, hasPlan, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInput(nextHour()))
  const [weight, setWeight] = useState('40000')
  const [interval, setIntervalMi] = useState<Interval>(25)
  // Picker bounds only guide the user; the API re-checks departure on submit.
  const [bounds] = useState(() => {
    const now = new Date()
    return { min: toLocalInput(now), max: toLocalInput(new Date(now.getTime() + MAX_DAYS_AHEAD * 86_400_000)) }
  })

  const weightLb = Number(weight)
  const weightOk = Number.isFinite(weightLb) && weightLb >= 1 && weightLb <= 150_000
  const ready = !!origin && !!destination && !!departure && weightOk

  function submit(withInterval = interval) {
    if (!ready) return
    onSubmit({
      origin: { lon: origin.lon, lat: origin.lat },
      destination: { lon: destination.lon, lat: destination.lat },
      departure: new Date(departure).toISOString(),
      weight_lb: weightLb,
      interval_mi: withInterval,
    })
  }


  return (
    <form
      className="trip-form"
      aria-busy={loading}
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} disabled={loading} />
      <PlaceInput label="Destination" value={destination} onChange={setDestination} disabled={loading} />

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            required
            value={departure}
            min={bounds.min}
            max={bounds.max}
            disabled={loading}
            onChange={(e) => setDeparture(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="weight">Load weight (lb)</label>
          <input
            id="weight"
            type="number"
            inputMode="numeric"
            min={1}
            max={150000}
            step={500}
            required
            value={weight}
            aria-invalid={!weightOk}
            disabled={loading}
            onChange={(e) => setWeight(e.target.value)}
          />
        </div>
      </div>

      <fieldset className="field segmented" disabled={loading}>
        <legend>Weather checkpoint every</legend>
        {INTERVALS.map((n) => (
          <label key={n}>
            <input
              type="radio"
              name="interval"
              value={n}
              checked={interval === n}
              onChange={() => {
                setIntervalMi(n)
                if (hasPlan) submit(n) // the plan on screen should match the selected interval
              }}
            />
            <span>{n} mi</span>
          </label>
        ))}
      </fieldset>

      <button type="submit" className="primary" disabled={!ready || loading}>
        {loading ? 'Planning routes…' : 'Plan routes'}
      </button>
    </form>
  )
}
