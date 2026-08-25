from pathlib import Path
import argparse
import hashlib

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.txt"

# Manifest integrity is intentionally scoped to release-critical files.
# Historical QA notes and other non-runtime documents may remain in a Git repo
# after a GitHub Desktop "replace files" update and must not make a clean CI
# checkout disagree with a manifest produced from the update package.
INCLUDED_TOP_LEVEL_FILES = {
    ".gitignore",
    "app.py",
    "VERSION.txt",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Dockerfile.api",
    "docker-compose.staging.yml",
}
INCLUDED_TOP_LEVEL_DIRS = {
    ".github",
    ".streamlit",
    "assets",
    "cupnavi_api",
    "cupnavi_core",
    "e2e",
    "public_pwa",
    "scripts",
    "staging",
    "static",
    "tests",
}
EXCLUDED_PARTS = {".git", ".pytest_cache", "__pycache__", ".idea", ".vscode", "backups", ".venv", "venv", "dist", "build"}
EXCLUDED_NAMES = {"RELEASE_MANIFEST.txt", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".bak", ".tmp"}
EXCLUDED_ENDINGS = (".db-shm", ".db-wal")


def is_release_file(path: Path, rel: Path) -> bool:
    if len(rel.parts) == 1:
        if rel.as_posix() not in INCLUDED_TOP_LEVEL_FILES:
            return False
    elif rel.parts[0] not in INCLUDED_TOP_LEVEL_DIRS:
        return False
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.staging.example":
        return False
    if path.as_posix().endswith(".streamlit/secrets.toml"):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.lower().endswith(EXCLUDED_ENDINGS):
        return False
    return True


def release_files():
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if is_release_file(path, rel):
            files.append(rel)
    return sorted(files, key=lambda p: p.as_posix().casefold())


def render():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    lines = ["# CupNavi release manifest", f"# version: {version}", "# sha256  path"]
    for rel in release_files():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  ./{rel.as_posix()}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        actual = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if actual != expected:
            raise SystemExit("RELEASE_MANIFEST.txt is stale. Run scripts/generate_release_manifest.py")
        print("Release manifest OK")
    else:
        MANIFEST.write_text(expected, encoding="utf-8")
        print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
