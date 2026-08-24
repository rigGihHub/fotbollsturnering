from __future__ import annotations
from pathlib import Path
import sys, json, os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from cupnavi_api.repository import public_snapshot, backend_name
from cupnavi_core.public_parity import compare_public_payloads

def main():
    key=os.getenv("CUPNAVI_PARITY_CUP","").strip()
    if not key:
        print("SKIP: CUPNAVI_PARITY_CUP is not set.")
        return 0
    snap=public_snapshot(key)
    if not snap:
        print(f"FAIL: published cup not found: {key}")
        return 2

    # Both sides are intentionally materialized independently, even though they
    # currently share the same repository in this executable check. This gate is
    # primarily for data semantics and future backend/frontend migrations.
    legacy_matches=[dict(m) for m in snap["matches"]]
    api_matches=[dict(m) for m in public_snapshot(key)["matches"]]
    legacy_brackets=[dict(b) for b in snap["brackets"]]
    api_brackets=[dict(b) for b in public_snapshot(key)["brackets"]]

    result=compare_public_payloads(
        tournament=snap["tournament"],
        teams=snap["teams"],
        groups=snap["groups"],
        legacy_matches=legacy_matches,
        api_matches=api_matches,
        legacy_brackets=legacy_brackets,
        api_brackets=api_brackets,
    )
    print(json.dumps({
        "backend":backend_name(),
        "cup":key,
        "ok":result.ok,
        "checks":result.checks,
        "details":result.details,
    },ensure_ascii=False,indent=2))
    return 0 if result.ok else 3

if __name__=="__main__":
    raise SystemExit(main())
