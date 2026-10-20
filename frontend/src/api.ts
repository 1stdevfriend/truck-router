import type { Place, Plan, PlanRequest } from './types'

// Production points at the Railway API; dev leaves it empty and uses the Vite proxy.
const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

/** Turn a DRF error body ({"field": ["msg"]} or {"error": "msg"}) into one readable line. */
function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object') {
    const b = body as Record<string, unknown>
    if (typeof b.error === 'string') return b.error
    const parts = Object.entries(b).map(([field, msgs]) => {
      const text = Array.isArray(msgs) ? msgs.join(' ') : typeof msgs === 'object' ? errorMessage(msgs, status) : String(msgs)
      return field === 'non_field_errors' ? text : `${field.replace(/_/g, ' ')}: ${text}`
    })
    if (parts.length) return parts.join(' · ')
  }
  return `Request failed (HTTP ${status})`
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_URL + url, init)
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new Error(errorMessage(body, res.status))
  return body as T
}

export async function geocode(q: string, signal: AbortSignal): Promise<Place[]> {
  const data = await request<{ results: Place[] }>(`/api/geocode?q=${encodeURIComponent(q)}`, { signal })
  return data.results
}

export function fetchPlan(body: PlanRequest): Promise<Plan> {
  return request<Plan>('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
