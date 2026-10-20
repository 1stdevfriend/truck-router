import type { RiskLevel } from './types'

export const RISK_LEVELS: RiskLevel[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_LABEL: Record<RiskLevel, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
}

export const RISK_COLOR: Record<RiskLevel, string> = {
  low: '#22c55e',
  moderate: '#facc15',
  high: '#f97316',
  severe: '#ef4444',
  no_travel: '#a855f7',
}

// Indexed by route id; kept clear of the risk colours so lines and markers don't blur together.
export const ROUTE_COLORS = ['#38bdf8', '#f472b6', '#e2e8f0']

export const formatTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })

export function formatDuration(hours: number) {
  const m = Math.round(hours * 60)
  return `${Math.floor(m / 60)} h ${m % 60} min`
}
