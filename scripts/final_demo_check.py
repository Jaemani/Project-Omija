"""One-command pre-demo verification for Project Omija.

Default mode checks the Foundry-backed demo path:

    uv run python scripts/final_demo_check.py

Use ``--full`` when there is enough time to also run the full local test suite
and deterministic evaluation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
FOUNDRY_HTML = OUT_DIR / "foundry_demo.html"
REQUIRED_OUTPUTS = (
    OUT_DIR / "demo_e2e_compare.json",
    OUT_DIR / "demo_e2e_foundry.json",
    OUT_DIR / "demo_e2e_sqlite.json",
    FOUNDRY_HTML,
)
HTML_MARKERS = (
    "Project Omija",
    "Risk band",
    "Impacted programs",
    "Active Path",
    "Provenance",
    "Raw record view",
)


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]


def build_steps(*, supplier: str, full: bool) -> list[Step]:
    python = sys.executable
    steps: list[Step] = []
    if full:
        steps.extend(
            [
                Step("Full test suite", (python, "-m", "pytest", "-q")),
                Step("Local evaluation", (python, "scripts/p6_eval.py")),
                Step("Local dashboard build", (python, "scripts/p4_dashboard.py")),
            ]
        )

    steps.extend(
        [
            Step(
                "Foundry OSDK link smoke",
                (python, "scripts/foundry_osdk_smoke.py", "--diagnose"),
            ),
            Step(
                "SQLite vs Foundry decision compare",
                (python, "scripts/demo_e2e.py", "--compare", "--supplier", supplier),
            ),
            Step(
                "Foundry HTML report",
                (python, "scripts/foundry_demo_report.py", supplier),
            ),
        ]
    )
    return steps


def _display_argv(argv: tuple[str, ...]) -> str:
    rendered: list[str] = []
    for part in argv:
        try:
            rendered.append(str(Path(part).relative_to(REPO_ROOT)))
        except (ValueError, OSError):
            rendered.append(part)
    return " ".join(rendered)


def run_step(step: Step) -> None:
    print(f"\n== {step.name}")
    print(f"$ {_display_argv(step.argv)}")
    started = time.time()
    proc = subprocess.run(
        step.argv,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    elapsed = time.time() - started
    if proc.returncode:
        raise SystemExit(f"FAILED {step.name} rc={proc.returncode} elapsed={elapsed:.1f}s")
    print(f"OK {step.name} elapsed={elapsed:.1f}s")


def verify_outputs() -> None:
    print("\n== Output files")
    missing = [path for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        raise SystemExit("FAILED missing outputs: " + ", ".join(str(p) for p in missing))

    html = FOUNDRY_HTML.read_text(encoding="utf-8")
    missing_markers = [marker for marker in HTML_MARKERS if marker not in html]
    if missing_markers:
        raise SystemExit("FAILED html missing markers: " + ", ".join(missing_markers))

    for path in REQUIRED_OUTPUTS:
        print(f"OK {path.relative_to(REPO_ROOT)} bytes={path.stat().st_size}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supplier", default="sup-h")
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run pytest, p6_eval, and p4_dashboard before Foundry checks",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for step in build_steps(supplier=args.supplier, full=args.full):
        run_step(step)
    verify_outputs()
    print("\nRESULT: READY")
    print(f"Open {FOUNDRY_HTML.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
