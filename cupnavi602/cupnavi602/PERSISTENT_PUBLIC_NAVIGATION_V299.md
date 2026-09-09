# CupNavi v1.299 – Persistent public navigation

The public Cupinfo / Schema / Tabeller / Slutspel / Statistik navigation now remains visible at the top of the viewport while the user scrolls through a public cup page.

## Root cause

The navigation element itself used `position: sticky`, but it is rendered inside a short Streamlit markdown element. A sticky descendant is constrained by that containing element, so the navigation could stop sticking as soon as its markdown wrapper scrolled away.

## Change

The Streamlit element containing `.cn-public-section-nav` is now the sticky element. The navigation itself remains in normal flow inside the sticky wrapper. This preserves the existing five-column layout, green row background, active-state styling, mobile labels and responsive breakpoints while keeping the menu available during vertical scrolling.

No tournament data, scheduling, results, publication, authentication or persistence logic is changed.
