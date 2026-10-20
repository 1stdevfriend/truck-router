import { useEffect, useId, useState } from 'react'
import { geocode } from './api'
import type { Place } from './types'

type Props = {
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
  disabled?: boolean
}

const DEBOUNCE_MS = 300

export default function PlaceInput({ label, value, onChange, disabled }: Props) {
  const id = useId()
  const [text, setText] = useState(value?.label ?? '')
  const [query, setQuery] = useState('') // what the user typed; empty = don't search
  const [results, setResults] = useState<Place[]>([])
  const [active, setActive] = useState(-1)
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')

  useEffect(() => {
    if (query.trim().length < 2) return
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      setStatus('loading')
      geocode(query.trim(), ctrl.signal)
        .then((places) => {
          setResults(places)
          setActive(-1)
          setOpen(true)
          setStatus('idle')
        })
        .catch((err) => {
          if (err.name !== 'AbortError') setStatus('error')
        })
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [query])

  function choose(place: Place) {
    setText(place.label)
    setQuery('')
    setOpen(false)
    onChange(place)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || !results.length) return
    if (e.key === 'ArrowDown') setActive((a) => (a + 1) % results.length)
    else if (e.key === 'ArrowUp') setActive((a) => (a <= 0 ? results.length - 1 : a - 1))
    else if (e.key === 'Enter' && active >= 0) choose(results[active])
    else if (e.key === 'Escape') setOpen(false)
    else return
    e.preventDefault()
  }

  const listId = `${id}-list`
  const showList = open && query.trim().length >= 2

  return (
    <div className="field place">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        aria-invalid={!!text && !value}
        autoComplete="off"
        placeholder="City, address or ZIP"
        value={text}
        disabled={disabled}
        onChange={(e) => {
          setText(e.target.value)
          setQuery(e.target.value)
          if (value) onChange(null) // typed over a chosen place: it no longer matches
        }}
        onKeyDown={onKeyDown}
        onBlur={() => setOpen(false)}
        onFocus={() => results.length && query && setOpen(true)}
      />
      {status === 'loading' && <span className="hint">Searching…</span>}
      {status === 'error' && <span className="hint error">Address search failed. Try again.</span>}
      {showList && (
        <ul id={listId} role="listbox" className="suggestions">
          {results.length === 0 && <li className="empty">No US matches</li>}
          {results.map((p, i) => (
            <li
              key={`${p.label}-${i}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => e.preventDefault()} // keep focus so blur doesn't close before click
              onClick={() => choose(p)}
            >
              {p.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
