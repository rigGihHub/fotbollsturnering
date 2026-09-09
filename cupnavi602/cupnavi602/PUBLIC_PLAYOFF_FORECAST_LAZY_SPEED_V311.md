# CupNavi v1.311 – Public playoff forecast lazy speed

## Problem
The public playoff page calculated all group tables on every rerun solely to prepare the collapsed playoff forecast. Streamlit expanders execute their body even when collapsed, so visitors paid this cost even when they never opened the forecast.

## Change
- Replaced the collapsed forecast expander with an explicit `Visa slutspelsprognos` toggle.
- `calculate_all_group_tables(...)` and `playoff_preview(...)` now run only after that opt-in.
- Existing bracket rendering, playoff validation and public data remain unchanged.
- Added an empty forecast caption when there is not yet enough table data.

## Scope
No database schema, schedule generation, results, publication, authentication, or concurrency/CAS write paths were changed.
