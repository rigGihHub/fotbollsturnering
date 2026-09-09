# v390 – Public share + toplist UX

## Problem

- Dela-popovern inherited the old global dark dialog styling. The share-specific light CSS already existed, but its marker was never rendered, so link/download button labels had insufficient contrast.
- Since v386, individual statistics live under Tabell instead of being a main navigation item. The remaining `Visa individuella topplistor` toggle was rendered after every group table, making Skytteliga/Assistliga hard to discover in larger tournaments.

## Changes

- The share popover now emits `.cn-share-popover-marker`, activating the existing scoped light popover styling and explicit button text contrast.
- `Tabell` now starts with a clear secondary `Tabeller / Topplistor` segmented control whenever individual leaderboards are enabled.
- Only the selected branch is rendered: opening Topplistor no longer calculates/renders all group tables first.
- Main public navigation remains intentionally compact: Matcher → Mitt lag → Tabell → Slutspel → Information.
