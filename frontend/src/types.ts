export type Place = { label: string; lon: number; lat: number }

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export type Interval = 10 | 25 | 50

export type PlanRequest = {
  origin: { lon: number; lat: number }
  destination: { lon: number; lat: number }
  departure: string // ISO 8601 with offset
  weight_lb: number
  interval_mi: Interval
}

export type Checkpoint = {
  mile: number
  lon: number
  lat: number
  eta: string
  segment_miles: number
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
  risk: RiskLevel
  risk_by: { wind: RiskLevel; rain: RiskLevel; snow: RiskLevel }
}

export type RouteResult = {
  id: number
  label: string
  source: string
  distance_mi: number
  duration_h: number
  arrival: string
  miles_by_level: Record<RiskLevel, number>
  avg_risk: number
  max_risk: RiskLevel
  geometry: [number, number][]
  checkpoints: Checkpoint[]
}

export type Plan = {
  departure: string
  interval_mi: Interval
  weight_lb: number
  recommended: number
  ranking: number[]
  reason: string
  warnings: string[]
  routes: RouteResult[]
}
