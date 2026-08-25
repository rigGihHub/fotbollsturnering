from pathlib import Path
import argparse
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.txt"

# Release integrity is deliberately based on an explicit, shallow allowlist.
# A Git repository updated by overlay/copy can contain stale historical copies of
# the whole project under legitimate directories such as scripts/, staging/ or
# cupnavi_core/. Those copies must never become release inputs.
INCLUDED_TOP_LEVEL_FILES = {
    ".gitignore",
    "app.py",
    "VERSION.txt",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Dockerfile.api",
    "docker-compose.staging.yml",
    "CLEANUP_LEGACY_DUPLICATES.bat",
}

# Patterns are relative to ROOT and intentionally shallow where the runtime
# structure is shallow. This is the key protection against nested stale repos.
INCLUDED_PATTERNS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".streamlit/config.toml",
    "assets/*",
    "cupnavi_api/*.py",
    "cupnavi_core/*.py",
    "e2e/*.py",
    "public_pwa/*",
    "scripts/*.py",
    "staging/Caddyfile",
    "staging/.env.staging.example",
    "static/*",
    "tests/*.py",
)

EXCLUDED_NAMES = {"RELEASE_MANIFEST.txt", ".DS_Store", "secrets.toml"}
EXCLUDED_PARTS = {"backups", "__pycache__", ".pytest_cache", ".git", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3", ".bak", ".tmp", ".log"}
EXCLUDED_ENDINGS = (".db-shm", ".db-wal")


def _allowed_candidates():
    seen = set()
    for name in INCLUDED_TOP_LEVEL_FILES:
        path = ROOT / name
        if path.is_file():
            rel = Path(name)
            if rel not in seen:
                seen.add(rel)
                yield path, rel
    for pattern in INCLUDED_PATTERNS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if rel not in seen:
                seen.add(rel)
                yield path, rel


def is_release_file(path: Path, rel: Path) -> bool:
    """Return True only for files belonging to the explicit release structure."""
    rel = Path(rel)
    if len(rel.parts) == 1:
        allowed = rel.as_posix() in INCLUDED_TOP_LEVEL_FILES
    else:
        allowed = False
        # Compare against the same shapes as INCLUDED_PATTERNS without relying
        # on recursive filesystem traversal.
        p = rel.as_posix()
        if len(rel.parts) == 3 and rel.parts[:2] == (".github", "workflows") and rel.suffix in {".yml", ".yaml"}:
            allowed = True
        elif p == ".streamlit/config.toml":
            allowed = True
        elif len(rel.parts) == 2 and rel.parts[0] == "assets":
            allowed = True
        elif len(rel.parts) == 2 and rel.parts[0] in {"cupnavi_api", "cupnavi_core", "e2e", "scripts", "tests"} and rel.suffix == ".py":
            # app.py is a project-root entry point; a copy inside scripts/ or
            # cupnavi_core/ is proof of a stale nested checkout, not a release file.
            allowed = not (rel.name == "app.py" and rel.parts[0] in {"scripts", "cupnavi_core"})
        elif len(rel.parts) == 2 and rel.parts[0] in {"public_pwa", "static"}:
            allowed = True
        elif p in {"staging/Caddyfile", "staging/.env.staging.example"}:
            allowed = True
        if not allowed:
            return False

    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if path.name == ".env":
        return False
    if rel.as_posix() == ".streamlit/secrets.toml":
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.lower().endswith(EXCLUDED_ENDINGS):
        return False
    return allowed


def release_files():
    files = []
    for path, rel in _allowed_candidates():
        if is_release_file(path, rel):
            files.append(rel)
    return sorted(set(files), key=lambda p: p.as_posix().casefold())


def render():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    lines = ["# CupNavi release manifest", f"# version: {version}", "# sha256  path"]
    for rel in release_files():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        lines.append(f"{digest}  ./{rel.as_posix()}")
    return "\n".join(lines) + "\n"


MANIFEST_LINE_RE = re.compile(r"^([0-9a-f]{64})  \./(.+)$")


def parse_manifest(text: str):
    version = None
    entries = {}
    for raw_line in text.splitlines():
        line = raw_line.strip("\n")
        if line.startswith("# version: "):
            version = line.removeprefix("# version: ").strip()
            continue
        match = MANIFEST_LINE_RE.match(line)
        if match:
            entries[match.group(2)] = match.group(1)
    return version, entries


def manifest_diagnostics(actual: str, expected: str):
    actual_version, actual_entries = parse_manifest(actual)
    expected_version, expected_entries = parse_manifest(expected)
    lines = ["RELEASE_MANIFEST.txt is stale."]
    if actual_version != expected_version:
        lines.append(f"VERSION: manifest={actual_version!r} expected={expected_version!r}")

    actual_paths = set(actual_entries)
    expected_paths = set(expected_entries)
    for path in sorted(expected_paths - actual_paths, key=str.casefold):
        lines.append(f"MISSING_FROM_MANIFEST: {path} expected_sha256={expected_entries[path]}")
    for path in sorted(actual_paths - expected_paths, key=str.casefold):
        lines.append(f"EXTRA_IN_MANIFEST: {path} manifest_sha256={actual_entries[path]}")
    for path in sorted(actual_paths & expected_paths, key=str.casefold):
        if actual_entries[path] != expected_entries[path]:
            lines.append(
                f"CHANGED: {path} manifest_sha256={actual_entries[path]} current_sha256={expected_entries[path]}"
            )

    if len(lines) == 1:
        actual_lines = actual.splitlines()
        expected_lines = expected.splitlines()
        max_len = max(len(actual_lines), len(expected_lines))
        for index in range(max_len):
            a = actual_lines[index] if index < len(actual_lines) else "<EOF>"
            e = expected_lines[index] if index < len(expected_lines) else "<EOF>"
            if a != e:
                lines.append(f"TEXT_DIFFERENCE line={index + 1} manifest={a!r} expected={e!r}")
                break
    lines.append("Regenerate with: python scripts/generate_release_manifest.py")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        actual = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if actual != expected:
            raise SystemExit(manifest_diagnostics(actual, expected))
        print("Release manifest OK")
    else:
        MANIFEST.write_text(expected, encoding="utf-8")
        print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
