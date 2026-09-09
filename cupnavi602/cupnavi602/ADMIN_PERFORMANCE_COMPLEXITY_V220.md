# CupNavi v.1.220 – Admin Performance & Complexity Audit

The shared Admin shell and Adminöversikt were audited because they execute on
normal Admin navigation reruns.

Optimizations:
- reuse the already loaded scheduled-match count for the schedule-state warning;
- reuse it again for publication/sidebar validation;
- reuse already loaded schedule rules in Adminöversikt;
- reuse the first Admin workflow-count snapshot for later UX progress;
- replace per-class team COUNT queries with one grouped query.

For N competition classes, the targeted Adminöversikt changes remove roughly
N + 3 net database reads. With two classes, that is about 5 fewer reads.

This is a query-count improvement, not a claimed wall-clock speedup.
No E2E/setup behavior, permissions, mutations, scheduling or result persistence
is changed.
