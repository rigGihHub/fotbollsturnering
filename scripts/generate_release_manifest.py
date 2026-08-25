from pathlib import Path
import argparse
import hashlib

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"RELEASE_MANIFEST.txt"
EXCLUDED_PARTS={".git",".pytest_cache","__pycache__",".idea",".vscode"}
EXCLUDED_NAMES={"RELEASE_MANIFEST.txt"}

def release_files():
    files=[]
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel=path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix==".pyc":
            continue
        files.append(rel)
    return sorted(files,key=lambda p:p.as_posix().casefold())

def render():
    version=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()
    lines=[f"# CupNavi release manifest",f"# version: {version}","# sha256  path"]
    for rel in release_files():
        digest=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  ./{rel.as_posix()}")
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    expected=render()
    if args.check:
        actual=MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if actual!=expected:
            raise SystemExit("RELEASE_MANIFEST.txt is stale. Run scripts/generate_release_manifest.py")
        print("Release manifest OK")
    else:
        MANIFEST.write_text(expected,encoding="utf-8")
        print(f"Wrote {MANIFEST}")

if __name__=="__main__":
    main()
