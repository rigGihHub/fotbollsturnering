# CupNavi v604 — Visual QA Contrast Hotfix

## Why
The first full dark-shell pass exposed two real visual regressions on the live landing page: the sidebar remained light in some Streamlit DOM layouts, and legacy landing/card text retained dark colors against the new dark background.

## Changes
- Targets the sidebar independently of `.stApp`, so the dark sidebar works across Streamlit mount variants.
- Converts the old light marketing hero to the CupNavi dark sports shell.
- Converts bordered Streamlit containers/cards to dark surfaces.
- Restores readable heading/body/caption contrast across legacy public content.
- Prevents secondary/link buttons from appearing as white bars.
- Preserves the intentionally light calendar popover.
- Keeps Text-TV styling independent and strongest in sports-data surfaces.

## Release intent
Visual hotfix only. No tournament logic, scoring, scheduling, permissions, or persisted data behavior is changed.
