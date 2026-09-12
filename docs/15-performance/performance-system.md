# Performance System

Performance is an implementation-efficiency problem, not a score-chasing exercise.

## Pipeline
Request -> DNS -> connection -> TLS -> HTTP -> server -> HTML -> DOM/CSSOM -> render tree -> layout -> paint -> composite -> frame -> interaction.

## Dimensions
- Network: DNS, latency, TLS, HTTP/2, HTTP/3, QUIC, CDN, edge, compression, caching, packet loss and mobile conditions.
- Loading: TTFB, FCP, LCP, resource priority, preload, lazy loading and critical path.
- Runtime: JavaScript execution, long tasks, main-thread contention, hydration and third-party code.
- Rendering: style calculation, layout, paint, compositing and frame stability.
- Stability: CLS, dimensions/reservations, font loading and dynamic content.
- Media: image/video dimensions, formats, quality, bitrate and responsive delivery.
- Size: HTML, CSS, JS, fonts, media, DOM size, request count and total transfer.
- Energy: CPU, memory, battery and device constraints.

## Visual preservation rule
Do not remove animation, graphics, effects, image quality or functionality merely to improve a metric. Find waste in delivery and implementation first.

## Validation
Measure before/after on representative mobile and desktop conditions; compare user-visible output and functional behavior; record regressions and retain evidence.
