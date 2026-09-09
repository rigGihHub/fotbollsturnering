# v412 – Publication flow order

A critical product audit found that the large Step 5 publication card was rendered globally before the Step 4 control page content. The visible planning flow could therefore read 5 → 4 even though the intended flow is Control → Publish.

This release:
- keeps the compact publication control in the sidebar on all admin pages,
- renders the large Step 5 publication card only after the Step 4 quick control summary,
- reuses the already-loaded schedule rules, scheduled-match count and cached validation snapshot on the control page,
- removes duplicate schedule-rules, validation and scheduled-match reads from the standard control path,
- preserves the existing critical/warning/improvement logic and publication concurrency guards.
