# CupNavi v.1.215 – Initial Setup Hardening, Phase 2

Focus: reduce unnecessary writes during Streamlit reruns without changing tournament behavior.

Changes:
- shared normalization/change detection for schedule-priority order;
- schedule priority JSON is written only when the effective order actually changes;
- team-request priorities compare desired rank with persisted rank;
- unchanged teams no longer receive redundant UPDATE statements;
- changed team ranks are persisted with one executemany transaction.

No forms were introduced in this phase. The setup relies on autosave, and moving existing widgets into forms would change interaction semantics. Streamlit documentation confirms that ordinary widgets rerun on changes while forms batch input until submit; this phase therefore optimizes writes without changing that UX contract.
