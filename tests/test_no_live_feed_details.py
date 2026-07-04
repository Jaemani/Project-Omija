"""Repository must not reintroduce live credential-feed implementation details."""

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}
SKIP_FILES = {
    Path("tests/test_no_live_feed_details.py"),
    Path("tests/test_stealthmole.py"),
}

FORBIDDEN = [
    "hackathon" + ".stealthmole",
    "api" + ".stealthmole",
    "STEALTHMOLE" + "_ACCESS_KEY",
    "STEALTHMOLE" + "_SECRET_KEY",
    "access" + "_key",
    "secret" + "_key",
    "Authorization" + ": Bearer",
    "HS" + "256",
    "sm" + "_headers",
    "src:" + "stealthmole:mock",
    "StealthMole" + " mock",
    'source="' + "stealthmole" + '"',
]


def iter_repo_text_files():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    for rel_text in result.stdout.splitlines():
        rel = Path(rel_text)
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        if rel in SKIP_FILES or any(part in SKIP_PARTS for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
            continue
        yield path


def test_live_feed_implementation_details_stay_redacted():
    offenders: list[str] = []
    for path in iter_repo_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in FORBIDDEN:
            if needle in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {needle}")

    assert offenders == []
