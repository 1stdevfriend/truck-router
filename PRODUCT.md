# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
A freight dispatcher at a desk (laptop) planning a truck trip before departure. They compare candidate routes, pick the safest sensible one, and pass it to the driver. The same flow is what Spotter assessment reviewers will walk through.

## Product Purpose
Truck Route Weather compares 3 truck (HGV) routes between two US places by the weather risk the truck will meet along each one. Success: the dispatcher sees, in one glance, which route is recommended and why, and where and when the risk sits along the way.

## Positioning
Risk is scored where the truck will be at each hour (forecast at each checkpoint's ETA), not "weather at origin and destination now". The load weight changes the wind risk.

## Operating Context
- Inputs: origin and destination (US address autocomplete), departure time (up to 14 days ahead), load weight in lb, and a checkpoint interval of 10, 25 or 50 mi.
- Outputs: 3 ranked routes, a recommendation with its deciding reason, warnings, per-route miles at each risk level, checkpoint details (ETA, wind/gust, rain, snow), and a 0–48 h risk heatmap with an hour slider.
- A plan can take up to about a minute (routing + forecast calls).

## Capabilities and Constraints
- Risk levels: Low, Moderate, High, Severe, No Travel. Ranking: No-Travel miles, then Severe miles, High miles, average risk, and finally travel time.
- Data: OpenRouteService (routing, geocoding), Open-Meteo (forecasts). No accounts, no database.
- Stack: Vite + React + TypeScript + MapLibre GL frontend (Vercel); Django + DRF backend (Railway).

## Brand Commitments
- Name: "Truck Route Weather".
- Binding visual request from the user: an orange background theme, motion/animation, and a truck animation while a plan loads.
- Results are shown on a full-screen map with a route side sheet (bottom sheet on mobile), not below the form.

## Evidence on Hand
No testimonials, customers or benchmarks exist. Do not invent any.

## Product Principles
1. The recommendation and its reason come first; details are one step away.
2. Risk is always shown with the time it applies to.
3. Risk colours mean the same thing everywhere (cards, markers, heatmap).
4. Never hide that a plan is loading or that a service failed.

## Accessibility & Inclusion
Risk must never be shown by colour alone: labels sit next to colour. Keyboard access for form, cards and slider; respect reduced motion.
