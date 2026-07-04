"""Live one-command recon: measure the LIVE StealthMole v2 contract.

What it does (PROMPTS.md P0-live, data-sources.md [확인필요] items):
  1. GET /user/quotas  → which modules are open + remaining credits.
  2. For the explicitly selected credential modules, exactly ONE /search on a
     synthetic/self-owned domain (default `supplier-a.example`, override with
     --domain). Each live search can cost multiple quota units, so the safe
     default is CDS only; no /export, retries, or mass queries.
  3. Record the response SCHEMA ONLY — field names, types, masked examples —
     to `out/p0b/schema_<module>.json` + console summary. Secrets never land
     in files or console: password/secret/cookie/token-family fields are
     masked (first 2 chars + `***`, adapter.base.mask_secret), every other
     string is truncated to 20 chars.
  4. If `cds` is open: highlight whether device/malware/infected_at/cookie
     fields exist — the live key measurement for active-compromise triage.

Run (user, after keys are issued — this run only with valid issued keys):
    uv run python scripts/p0b_recon.py [--domain supplier-a.example]
                                       [--modules cds,cl,cb] [--quotas-only]

Credentials: env `STEALTHMOLE_ACCESS_KEY` / `STEALTHMOLE_SECRET_KEY`
(or a repo-root `.env`, see `.env.example`). Missing keys → guidance + exit 0
(NOT an error — this script is meant to no-op safely before keys are issued and
in CI, doing ZERO network work).

After a successful run: promote data-sources.md [확인필요] → [검증됨] and adjust
`adapter/base.py normalize()` field mapping to the measured cds schema.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from adapter.base import mask_secret            # noqa: E402
from adapter.stealthmole import StealthMoleSource  # noqa: E402

DEFAULT_DOMAIN = "supplier-a.example"   # synthetic — never a real supplier
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "out", "p0b")

# Verified module codes first (data-sources.md §1), then possible extras.
# Hackathon reference: DT and UB are not provided. CDF/TT and monitoring
# modules use different search families and are not credential-pipe defaults.
KNOWN_MODULE_ORDER = ("cds", "cl", "cb", "cdf", "tt", "rm", "gm", "lm")
DEFAULT_MODULES = {"cds"}

# Field-name tokens that mark a value as a secret → mask, never truncate-only.
SENSITIVE_TOKENS = (
    "password", "passwd", "pwd", "pass", "secret", "cookie",
    "token", "session", "credential", "auth", "hash", "otp", "key",
)

# live key measurement: active-compromise field families expected in cds.
CDS_FIELD_FAMILIES: dict[str, tuple[str, ...]] = {
    "device": ("device", "machine", "computer", "hwid", "os", "hostname_pc"),
    "malware": ("malware", "stealer", "family"),
    "infected_at": ("infected", "infection", "compromised_at", "log_date"),
    "cookie": ("cookie", "session"),
}

MAX_SAMPLE_RECORDS = 3   # masked samples kept per module (schema evidence)
MAX_SCHEMA_RECORDS = 10  # records inspected for field-name/type union
STR_TRUNC = 20           # non-sensitive string example cutoff


# ---- env / credentials -------------------------------------------------------


def _load_dotenv(path: str) -> None:
    """Minimal .env loader (KEY=VALUE lines); never overrides existing env."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and value and key not in os.environ:
                os.environ[key] = value


def _require_keys() -> bool:
    if os.environ.get("STEALTHMOLE_ACCESS_KEY") and os.environ.get(
        "STEALTHMOLE_SECRET_KEY"
    ):
        return True
    print(
        "NOTE: StealthMole credentials not set — nothing to probe yet "
        "(this is NOT an error; exiting 0).\n"
        "\n"
        "  This is the live recon script. It needs the keys\n"
        "  issued to the hackathon account:\n"
        "\n"
        "    export STEALTHMOLE_ACCESS_KEY=...\n"
        "    export STEALTHMOLE_SECRET_KEY=...\n"
        "\n"
        "  or copy `.env.example` to `.env` (gitignored) at the repo root\n"
        "  and fill both values. NEVER commit real keys.\n"
        "\n"
        "  If live access is blocked, the pipe runs on the mock adapter\n"
        "  (`uv run python scripts/p0_pipe.py`).",
        file=sys.stderr,
    )
    return False


# ---- masking -----------------------------------------------------------------


def _is_sensitive(field_name: str) -> bool:
    name = field_name.lower()
    return any(tok in name for tok in SENSITIVE_TOKENS)


def _mask_value(field_name: str, value, seen_raw: set[str]):
    """Return a display-safe copy of `value`. Sensitive strings → 2 chars +
    `***`; other strings → 20-char truncation; containers recurse."""
    if isinstance(value, dict):
        return {k: _mask_value(k, v, seen_raw) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask_value(field_name, v, seen_raw) for v in list(value)[:3]]
    if isinstance(value, str):
        if _is_sensitive(field_name):
            if len(value) > 4:
                seen_raw.add(value)  # for the final leak assertion
            return mask_secret(value)
        return value[:STR_TRUNC]
    return value  # int / float / bool / None pass through


def _type_name(value) -> str:
    if value is None:
        return "null"
    return type(value).__name__


def _collect_fields(records: list[dict], seen_raw: set[str]) -> dict:
    """Union of field names over sampled records → {name: {types, example}}.
    Nested dicts are flattened with dotted paths; examples are masked."""
    fields: dict[str, dict] = {}

    def visit(prefix: str, obj: dict) -> None:
        for key, value in obj.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict):
                visit(f"{path}.", value)
                continue
            entry = fields.setdefault(path, {"types": set(), "example": None})
            entry["types"].add(_type_name(value))
            if entry["example"] is None and value is not None:
                entry["example"] = _mask_value(key, value, seen_raw)

    for rec in records[:MAX_SCHEMA_RECORDS]:
        if isinstance(rec, dict):
            visit("", rec)
    return {
        name: {"types": sorted(meta["types"]), "example": meta["example"]}
        for name, meta in sorted(fields.items())
    }


# ---- quotas ------------------------------------------------------------------


def _open_modules(quotas: dict) -> list[tuple[str, object]]:
    """Return ``(module_code, remaining)`` for provided hackathon modules."""
    by_code: dict[str, object] = {}
    for key, val in quotas.items():
        code = str(key).lower()
        if code in {"dt", "ub"}:
            continue
        if isinstance(val, dict):
            allowed = val.get("allowed")
            used = val.get("used", 0)
            remaining = allowed - used if isinstance(allowed, (int, float)) else allowed
        else:
            remaining = val
        by_code[code] = remaining
    ordered = [c for c in KNOWN_MODULE_ORDER if c in by_code]
    ordered += sorted(c for c in by_code if c not in KNOWN_MODULE_ORDER)
    return [(c, by_code[c]) for c in ordered]


# ---- cds highlight -----------------------------------------------------------


def _cds_field_report(field_names: list[str]) -> dict[str, list[str]]:
    """Map each active-compromise family → actual matching field names."""
    def hits(low: str, token: str) -> bool:
        # Short tokens ("os") match only whole path segments to avoid false
        # positives like "host"; longer tokens match as substrings.
        if len(token) <= 2:
            return token in low.replace(".", "_").split("_")
        return token in low

    report: dict[str, list[str]] = {}
    lowered = [(f, f.lower()) for f in field_names]
    for family, tokens in CDS_FIELD_FAMILIES.items():
        report[family] = sorted(
            {orig for orig, low in lowered if any(hits(low, t) for t in tokens)}
        )
    return report


# ---- main flow ---------------------------------------------------------------


def run(
    source: StealthMoleSource,
    domain: str = DEFAULT_DOMAIN,
    out_dir: str = DEFAULT_OUT_DIR,
    modules_filter: set[str] | None = None,
    quotas_only: bool = False,
) -> int:
    print("=" * 68)
    print("Live recon: StealthMole v2 live contract measurement")
    print(f"query domain: {domain}  (synthetic/self-owned only — 1 call/module)")
    print("=" * 68)

    # -- (1) quotas ----------------------------------------------------------
    print("\n[1/3] GET /user/quotas")
    try:
        quotas = source.quotas()
    except Exception as exc:  # auth/network — nothing else can work
        print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "  → check exact keys, account/API product activation, UTC clock skew, and network.",
            file=sys.stderr,
        )
        return 1

    modules = _open_modules(quotas)
    if not modules:
        print(f"  no modules in quotas response: {json.dumps(quotas)[:200]}")
        return 1
    for code, remaining in modules:
        print(f"  {code:<6} remaining={remaining}")

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "quotas.json"), "w", encoding="utf-8") as fh:
        json.dump(quotas, fh, indent=2, ensure_ascii=False)
    print(f"  → {os.path.relpath(os.path.join(out_dir, 'quotas.json'), REPO_ROOT)}")

    if quotas_only:
        print("\n--quotas-only: stopping before any /search (0 credits spent).")
        return 0

    # -- (2)+(3) one /search per open module → schema files ------------------
    print(f"\n[2/3] per-module /search (exactly once each, domain={domain})")
    seen_raw: set[str] = set()
    cds_fields: list[str] = []
    failures: list[str] = []
    probed = 0

    for code, remaining in modules:
        if modules_filter is not None and code not in modules_filter:
            print(f"  {code:<6} skipped (--modules filter)")
            continue
        if isinstance(remaining, (int, float)) and remaining <= 0:
            print(f"  {code:<6} skipped (remaining={remaining}, no credit)")
            continue

        try:
            records = source.search(code, "domain", domain)
        except Exception as exc:
            print(f"  {code:<6} FAILED: {type(exc).__name__}: {exc}")
            failures.append(code)
            continue

        probed += 1
        fields = _collect_fields(records, seen_raw)
        response_meta = getattr(source, "last_response_meta", {})
        schema = {
            "module": code,
            "query": f"domain:{domain}",
            "fetched_at": int(time.time()),
            "record_count": len(records),
            "response_meta": response_meta,
            "fields": fields,
            "samples_masked": [
                _mask_value("", r, seen_raw) if isinstance(r, dict) else r
                for r in records[:MAX_SAMPLE_RECORDS]
            ],
            "masking": "sensitive fields: first 2 chars + '***'; other strings cut to 20 chars",
        }

        # Leak assertion: no raw sensitive value may survive into the output.
        blob = json.dumps(schema, ensure_ascii=False)
        leaked = [s for s in seen_raw if s in blob]
        if leaked:
            print(
                f"  {code:<6} ABORTED WRITE: masking failed for "
                f"{len(leaked)} value(s) — file not written",
                file=sys.stderr,
            )
            failures.append(code)
            continue

        path = os.path.join(out_dir, f"schema_{code}.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(blob)
        print(
            f"  {code:<6} {len(records):>3} records, {len(fields):>2} fields, "
            f"cost={response_meta.get('queryCost', 'unknown')} "
            f"→ {os.path.relpath(path, REPO_ROOT)}"
        )
        if fields:
            print(f"         fields: {', '.join(fields)}")
        elif not records:
            print(
                "         (0 records — schema unknown; retry with a domain "
                "you control via --domain)"
            )
        if code == "cds":
            cds_fields = list(fields)

    # -- (4) cds active-compromise field highlight ---------------------------
    print("\n[3/3] cds active-compromise fields (live key measurement)")
    if cds_fields:
        report = _cds_field_report(cds_fields)
        for family, matched in report.items():
            status = f"PRESENT ({', '.join(matched)})" if matched else "MISSING"
            print(f"  {family:<12}: {status}")
        missing = [f for f, m in report.items() if not m]
        if missing:
            print(
                f"  → adjust adapter/base.py normalize() for missing: "
                f"{', '.join(missing)}; update data-sources.md §5."
            )
        else:
            print("  → all families present: promote [확인필요] → [검증됨].")
    else:
        print("  (no cds fields captured — module closed, filtered, or 0 records)")

    print("\n" + "-" * 68)
    print(
        f"probed {probed} module(s), {len(failures)} failure(s)"
        + (f": {', '.join(failures)}" if failures else "")
    )
    print("next: data-sources.md [확인필요] → 실측값 반영, normalize() 매핑 조정")
    print("=" * 68)
    return 1 if (probed == 0 or failures) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Live one-command StealthMole v2 recon (quotas → 1 search "
        "per open module → masked schema files)."
    )
    parser.add_argument(
        "--domain",
        default=DEFAULT_DOMAIN,
        help=f"synthetic/self-owned domain to query (default: {DEFAULT_DOMAIN})",
    )
    parser.add_argument(
        "--modules",
        default=",".join(sorted(DEFAULT_MODULES)),
        help="comma-separated module codes to probe (default: cds only), "
        "e.g. --modules cds,cl,cb; DT/UB are unavailable",
    )
    parser.add_argument(
        "--quotas-only",
        action="store_true",
        help="only call /user/quotas; spend zero search credits",
    )
    args = parser.parse_args(argv)

    _load_dotenv(os.path.join(REPO_ROOT, ".env"))
    if not _require_keys():
        return 0  # missing keys is not an error (CLAUDE.md: no-op safely, 0 network)

    modules_filter = (
        {m.strip().lower() for m in args.modules.split(",") if m.strip()}
        if args.modules
        else None
    )
    return run(
        StealthMoleSource(),
        domain=args.domain,
        modules_filter=modules_filter,
        quotas_only=args.quotas_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
