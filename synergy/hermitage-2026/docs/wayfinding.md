# Hermitage 2026 wayfinding

## Purpose

A public, read-only, mobile-first visitor aid for the State Hermitage in Saint Petersburg.
It reduces orientation errors by organizing the museum into seven collapsible floor modules:

- Main Museum Complex: floors 1, 2, 3.
- General Staff Building: floors 1, 2, 3, 4.

Each floor is further divided into visitor-facing blocks with:
- a start anchor;
- landmark chain;
- reset point when the visitor is lost;
- official virtual-floor link;
- official PDF link;
- 2GIS indoor-routing link.

## Truth boundary

This site is not an official museum map and does not claim centimeter-level geometry.
The State Hermitage states that 2GIS includes floor-by-floor plans for the Main Museum
Complex and General Staff Building and can route to a place of interest, including stairs
and turns. Therefore this site uses 2GIS/official floor plans for the final indoor segment.

Room numbers are shown only where supported by the official room/floor index, official
digital-collection metadata, or an explicit number-derived floor rule. Collection placement
can change. A visitor should re-check current signage and official sources on the visit day.

The 1–10 crowd score is an expert wayfinding heuristic, not an official live occupancy
measurement. No complete comparable room-level attendance dataset was found in the
official sources used for this candidate.

## UX / accessibility

- Native `<details>/<summary>` disclosure widgets.
- Progressive enhancement: floor navigation works without JavaScript.
- Search and filters enhance the static floor plan.
- `prefers-reduced-motion` respected.
- Keyboard-visible skip link.
- No runtime third-party JavaScript.
- Strict CSP with `script-src 'self'` and `style-src 'self'`.

## Source hierarchy

1. State Hermitage official visit / room / virtual-floor pages.
2. State Hermitage official statement about 2GIS indoor routing.
3. Existing Synergy GitHub Pages donor (`synergy/289-roles/`) for publication/security patterns.
4. MDN native semantic HTML patterns.
5. Minimal new glue only.

## Rollback

The artifact is isolated under `synergy/hermitage-2026/`.
Rollback is a normal reviewed revert of this path or closure of the Draft PR before merge.

## Floor tabs and visitor-exit reset

- The landing page exposes seven keyboard-reachable floor-tab links that deep-link to the seven existing floor modules without requiring JavaScript.
- Every floor module contains an explicit ordinary-visitor exit/reset hint. These hints intentionally defer to current museum signage and staff when circulation changes.
- The site does **not** claim to be an evacuation plan and must not invent emergency egress geometry. In an emergency, visitors should follow on-site signage, announcements, and staff instructions.
- This preserves progressive enhancement: floor content remains readable when JavaScript or the 100-place JSON fails.
