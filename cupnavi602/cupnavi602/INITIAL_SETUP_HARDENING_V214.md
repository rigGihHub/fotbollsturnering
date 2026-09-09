# CupNavi v.1.214 – Initial Tournament Setup Hardening, Phase 1

## Audit
`render_initial_tournament_setup()` is currently 464 lines and still combines:
- capacity calculations
- sport defaults
- format recommendations
- rules
- schedule priorities
- service options
- final setup validation

## Verified issues addressed

### Duplicated capacity calculation
The setup previously calculated pitch-window minutes and occupied match-slot length in two separate places:
1. capacity metrics;
2. format recommendation.

Both now use `cupnavi_core.initial_setup_logic.py`.

This creates one testable definition for:
- confirmed pitch-window minutes;
- occupied match length;
- estimated capacity slots.

### Optional service fields always visible
The setup always rendered:
- Information om omklädningsrum
- Priser/avgifter

even when the corresponding checkbox was off.

They now use progressive disclosure and appear only when enabled.

Previously stored text is not cleared when the option is disabled; the database value remains unchanged and is restored when the option is enabled again.

## Explicitly unchanged
- tournament schema
- autosave callbacks
- schedule generation
- lifecycle protection
- sport profiles
- format recommendation algorithm
- team/group data
- result/history rules
- permissions

## Next candidate
Phase 2 should audit setup reruns and write frequency, especially drag-and-drop priorities and team-request prioritization. Do not refactor the whole setup as one unit.
