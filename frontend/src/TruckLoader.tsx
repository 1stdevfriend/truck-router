import { useEffect, useState } from 'react'

/** Full-screen loading state: a truck driving down the road while the plan is built. */
export default function TruckLoader() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="loader" role="status" aria-live="polite">
      <svg className="scene" viewBox="0 0 480 170" aria-hidden="true">
        <g className="clouds">
          <path className="cloud c1" d="M40 46a14 14 0 0 1 27-5 11 11 0 0 1 16 10H34a8 8 0 0 1 6-5z" />
          <path className="cloud c2" d="M40 46a14 14 0 0 1 27-5 11 11 0 0 1 16 10H34a8 8 0 0 1 6-5z" />
          <path className="cloud c3" d="M40 46a14 14 0 0 1 27-5 11 11 0 0 1 16 10H34a8 8 0 0 1 6-5z" />
        </g>
        <rect className="road" x="0" y="132" width="480" height="38" />
        <g className="dashes">
          {Array.from({ length: 14 }, (_, i) => (
            <rect key={i} x={i * 40} y="149" width="22" height="4" rx="2" />
          ))}
        </g>
        <g className="truck">
          <g className="puffs">
            <circle className="puff p1" cx="303" cy="58" r="5" />
            <circle className="puff p2" cx="303" cy="58" r="5" />
          </g>
          <rect className="trailer" x="128" y="58" width="150" height="62" rx="5" />
          <path className="mark" d="M203 74l15 15-15 15-15-15z" />
          <rect className="hitch" x="276" y="110" width="16" height="6" />
          <path className="cab" d="M286 120V78a8 8 0 0 1 8-8h30a10 10 0 0 1 8 4l18 24a10 10 0 0 1 2 6v16z" />
          <path className="window" d="M312 78h12a4 4 0 0 1 3 1.6l11 14.4h-26z" />
          <rect className="stack" x="298" y="56" width="5" height="22" rx="1" />
          {[156, 184, 304, 336].map((cx) => (
            <g key={cx} className="wheel" style={{ transformOrigin: `${cx}px 122px` }}>
              <circle cx={cx} cy="122" r="12" />
              <circle className="hub" cx={cx} cy="122" r="4.5" />
              <rect className="spoke" x={cx - 1} y="111" width="2" height="7" />
            </g>
          ))}
        </g>
      </svg>
      <h2>Planning your routes</h2>
      <p className="elapsed" aria-hidden="true">
        {seconds} s
      </p>
    </div>
  )
}
