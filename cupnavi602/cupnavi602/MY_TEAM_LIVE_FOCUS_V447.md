# CupNavi v447 — My Team Live Focus

## Goal
Make the first mobile screen in **Mitt lag / Min cup** more useful on cup day without adding first-paint database work.

## Changes
- Live and halftime status now wins over already-entered score fields in the favorite-team snapshot. A 1–0 live match can no longer be mistaken for a finished result.
- The primary next-match action adapts to the situation: **Följ matchen nu**, **Öppna matchen · paus**, **Nästa match om X min**, or the normal **Öppna nästa match**.
- The lazy directions control now sits immediately below the primary match action and names the pitch directly.
- Venue lookup remains fully lazy; opening Mitt lag performs no extra database read for directions.
- Live/halftime matches are excluded from played-count/latest-result calculations until they are actually finished.

## Performance rule
The first paint continues to use only the already loaded public team/match snapshot. Venue data is fetched only after an explicit directions toggle.
