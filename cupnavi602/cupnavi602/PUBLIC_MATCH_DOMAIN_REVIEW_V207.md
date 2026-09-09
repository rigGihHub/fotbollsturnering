# CupNavi v.1.207 – Public Match Domain Review

## Result after phases 1–3
The public match domain has been split into dedicated responsibilities:
- `public_match_cards.py` – match-card presentation
- `public_match_filter_logic.py` – pure filter/sort logic
- `public_match_feed_logic.py` – live/upcoming/recent classification
- `public_match_filters_view.py` – Streamlit filter panel

`render_public_view()` is now 813 lines and the former 124-line filter panel is reduced to a thin adapter in the main file.

## Why this extraction was selected
The remaining filter panel was the largest clearly bounded UI responsibility inside the public match page. Moving it out reduces the main-file change surface without touching database access, results, scheduling, event persistence or lifecycle rules.

## Preserved
- Streamlit widget keys and session behavior
- filter labels and options
- forced-team filter behavior
- age/group/team/pitch filtering
- sorting order
- URL/public-page behavior

## Next recommendation
Do not continue extracting mechanically. The next step should be a regression and performance review of the public match domain, then only extract another unit if it has a clear stability or testability benefit.
