# CupNavi 2026.09.09-602-KIT-IDENTITY-DISAMBIGUATION

CupNavi now handles ambiguous team names before trusting kit colours. If several plausible clubs are found, the organiser selects the correct club from 2–4 sourced candidates and CupNavi then runs a targeted shirt search. Ambiguous results are never presented as verified shirts.

The change keeps v601's fast path: candidate discovery is part of the same initial web-search response, the 12-hour cache remains, the search still has a maximum of two evidence passes, and whole-tournament scans remain parallelized up to four teams.

Current release gate: PASS (302 evergreen passed / 2 intentional deselections + 166 selected current regression tests passed).
