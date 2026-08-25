from __future__ import annotations
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]

# Only remove paths that are unmistakably stale copies of the project inside
# directories that have a legitimate primary purpose.
NESTED_REPO_DIR_NAMES = {
    ".github", "assets", "cupnavi_api", "e2e", "public_pwa", "static", "tests"
}
ROOT_COPY_FILES = {
    "app.py", "VERSION.txt", "requirements.txt", "requirements-dev.txt",
    "pyproject.toml", "Dockerfile.api", "docker-compose.staging.yml",
    "RELEASE_MANIFEST.txt",
}


def legacy_paths():
    found = []
    # scripts/: legitimate contents are direct Python helper scripts only.
    scripts = ROOT / "scripts"
    if scripts.exists():
        for child in scripts.iterdir():
            if child.is_dir() and child.name in NESTED_REPO_DIR_NAMES | {"cupnavi_core", "scripts", "staging"}:
                found.append(child)
            elif child.is_file() and child.name in ROOT_COPY_FILES:
                found.append(child)

    # staging/: legitimate contents are Caddyfile and .env.staging.example only.
    staging = ROOT / "staging"
    if staging.exists():
        for child in staging.iterdir():
            if child.name in {"Caddyfile", ".env.staging.example"}:
                continue
            if child.is_dir() or child.name in ROOT_COPY_FILES:
                found.append(child)

    # cupnavi_core/: legitimate contents are direct Python package files only.
    core = ROOT / "cupnavi_core"
    if core.exists():
        for child in core.iterdir():
            if child.is_dir():
                found.append(child)
            elif child.is_file() and child.suffix != ".py":
                found.append(child)
            elif child.is_file() and child.name == "app.py":
                found.append(child)
    return sorted(set(found), key=lambda p: p.as_posix().casefold())


def main():
    parser = argparse.ArgumentParser(description="Remove stale nested CupNavi repo copies left by old overlay updates.")
    parser.add_argument("--apply", action="store_true", help="Actually delete detected stale paths.")
    args = parser.parse_args()
    found = legacy_paths()
    if not found:
        print("No legacy nested CupNavi copies found.")
        return 0
    print("Legacy nested CupNavi paths detected:")
    for path in found:
        print(f" - {path.relative_to(ROOT).as_posix()}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to remove them.")
        return 1
    for path in found:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    print(f"Removed {len(found)} stale paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
