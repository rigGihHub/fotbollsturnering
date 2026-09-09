# CupNavi v1.290 – Admin information hierarchy polish

## Goal
Reduce repeated UI chrome and competing guidance in Admin without removing functionality or changing domain behavior.

## Changes
- Removed the redundant sidebar `Visningsläge` caption; the active role is already visible in the role switcher.
- Removed the extra `Administration` label above the admin navigation.
- Removed the repeated selected admin-group heading below the already-highlighted group button.
- Suppressed the global `Nästa steg` callout on Adminöversikt, where the overview already owns richer next-step guidance.
- Kept the global next-step callout on the other primary workflow pages.
- Kept all five admin groups, primary/advanced page navigation, global cup search, publication controls and page content unchanged.

## Risk profile
Presentation-only change. No database schema, schedule engine, result write, auth, publication or concurrency/CAS logic changed.

## Verification
See release test output. Browser E2E, physical Android/iPhone and live deployment are not claimed unless separately verified.
