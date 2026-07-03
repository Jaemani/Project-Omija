"""P1 vertical slice: registry → mock query → normalize → CorrelateExposure →
ontology write → screen.

Pipeline (no network, no secrets):
  1. load registry/suppliers.yaml into the ontology store (Supplier·Domain·
     Prime·Program + supplies/runs links),
  2. mock adapter → normalize() (masking enforced) → write_exposure (unattributed),
  3. CorrelateExposure: attribute each Exposure to a Supplier by email-domain
     match (records match_basis provenance),
  4. render a static report (out/p1_report.html) + print a CLI summary.

The report highlights ACTIVE signals (recent stealer + live session cookie on a
vpn/admin account) at the top and cites every exposure's source_ref. Raw secrets
are never emitted — only masked values reach the store or the screen.

Run: `uv run python scripts/p1_report.py`  (writes out/p1_report.html)
"""

from __future__ import annotations

import html
import os
import sys
from datetime import datetime, timezone

# Repo root on path (script may be run directly).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.correlate import CorrelationResult, correlate_exposures        # noqa: E402
from adapter.base import normalize                                          # noqa: E402
from adapter.mock import DAY, DEMO_NOW, MODULES, MockExposureSource         # noqa: E402
from registry.loader import load_into_store, load_registry                 # noqa: E402
from store.sqlite import SqliteOntologyStore                               # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
OUT_HTML = os.path.join(OUT_DIR, "p1_report.html")

# Active-compromise recency window (relative to the mock demo clock).
ACTIVE_WINDOW = 14 * DAY

# criticality (registry numeric 1..3) → display label.
_CRIT_LABEL = {3: "high", 2: "medium", 1: "low"}


def is_active(row: dict, now: int) -> bool:
    """Path precondition for FlagActiveCompromise (P3): recent stealer device
    holding a live session cookie on a vpn/admin account."""
    return bool(
        row.get("has_session_cookie")
        and row.get("account_type") in {"vpn", "admin"}
        and row.get("infected_at") is not None
        and (now - int(row["infected_at"])) <= ACTIVE_WINDOW
    )


def build_store() -> tuple[SqliteOntologyStore, CorrelationResult, int]:
    """Run the full P1 pipe into a fresh in-memory store. Returns (store,
    correlation result, records written)."""
    store = SqliteOntologyStore(":memory:")

    # 1) Registry → ontology (Supplier·Domain·Prime·Program + supplies/runs).
    load_into_store(store, load_registry())

    # 2) mock → normalize → write (unattributed; correlation attributes below).
    source = MockExposureSource()
    written = 0
    for fqdn in source.domains():
        for module in MODULES:
            for raw in source.search(module, "domain", fqdn):
                store.write_exposure(normalize(module, raw))
                written += 1

    # 3) CorrelateExposure (email-domain → Supplier, records match_basis).
    result = correlate_exposures(store, now=DEMO_NOW)
    return store, result, written


# ---------------------------------------------------------------------------
# HTML rendering (self-contained; masked values only)
# ---------------------------------------------------------------------------


def _fmt_ts(ts: int | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


def _e(v) -> str:
    return html.escape("" if v is None else str(v))


def _propagation_str(store: SqliteOntologyStore, supplier_id: str) -> str:
    rows = store.propagation_for_supplier(supplier_id)
    primes = {}
    for r in rows:
        primes.setdefault(r["prime_name"] or r["prime_id"], [])
        if r.get("program_name"):
            primes[r["prime_name"] or r["prime_id"]].append(r["program_name"])
    parts = []
    for prime, progs in primes.items():
        progs_txt = ", ".join(sorted(set(progs))) if progs else "—"
        parts.append(f"{_e(prime)} → [{_e(progs_txt)}]")
    return " ; ".join(parts) if parts else "—"


def _exposure_row_html(r: dict, active: bool) -> str:
    badge = '<span class="badge active">ACTIVE</span>' if active else ""
    secret = _e(r.get("masked_value") or "—")
    threat = _e(r.get("threat_kind") or "—")
    dev = ""
    if r.get("infected_at"):
        dev = (f'<div class="dev">malware={_e(r.get("malware") or "—")} · '
               f'acct={_e(r.get("account_type") or "—")} · '
               f'cookie={"yes" if r.get("has_session_cookie") else "no"} · '
               f'infected={_fmt_ts(r.get("infected_at"))}</div>')
    return (
        f'<tr class="{"active-row" if active else ""}">'
        f'<td>{_e(r.get("module"))} {badge}</td>'
        f'<td>{threat}</td>'
        f'<td class="mono">{_e(r.get("host") or "—")}</td>'
        f'<td>{_fmt_ts(r.get("observed_at"))}</td>'
        f'<td>{_fmt_ts(r.get("fetched_at"))}</td>'
        f'<td class="mono secret">{_e(r.get("secret_type"))}: {secret}</td>'
        f'<td class="mono ref" title="{_e(r.get("match_basis") or "")}">{_e(r.get("source_ref"))}</td>'
        f'</tr>{("<tr class=devrow><td colspan=7>" + dev + "</td></tr>") if dev else ""}'
    )


def _supplier_section_html(store: SqliteOntologyStore, sup: dict, now: int) -> tuple[str, bool, int, int]:
    rows = store.exposures_for_supplier(sup["id"])
    active_rows = [r for r in rows if is_active(r, now)]
    # Active exposures first, then rest.
    ordered = active_rows + [r for r in rows if r not in active_rows]
    crit = sup.get("criticality")
    crit_label = _CRIT_LABEL.get(crit, str(crit)) if crit is not None else "—"
    prop = _propagation_str(store, sup["id"])
    flag = '<span class="badge active">ACTIVE COMPROMISE</span>' if active_rows else (
        '<span class="badge clean">clean</span>' if not rows else '<span class="badge">exposed</span>')

    if not rows:
        body = '<p class="muted">no correlated exposures.</p>'
    else:
        trs = "".join(_exposure_row_html(r, is_active(r, now)) for r in ordered)
        body = (
            '<table><thead><tr>'
            '<th>module</th><th>threat source</th><th>source host</th>'
            '<th>observed</th><th>fetched</th><th>secret (masked)</th><th>source_ref</th>'
            '</tr></thead><tbody>' + trs + '</tbody></table>'
        )

    section = (
        f'<section class="supplier {"has-active" if active_rows else ""}">'
        f'<h3>{_e(sup["name"])} <span class="sid">{_e(sup["id"])}</span> {flag}</h3>'
        f'<div class="meta">tier T{_e(sup.get("tier"))} · criticality {_e(crit_label)} · '
        f'exposures {len(rows)} · active {len(active_rows)}</div>'
        f'<div class="prop">propagation: {prop}</div>'
        f'{body}</section>'
    )
    return section, bool(active_rows), len(rows), len(active_rows)


def build_report_html(store: SqliteOntologyStore, result: CorrelationResult, now: int) -> str:
    suppliers = store.suppliers()
    # Order: active suppliers first, then by exposure count desc, then id.
    def sort_key(sup):
        rows = store.exposures_for_supplier(sup["id"])
        act = any(is_active(r, now) for r in rows)
        return (0 if act else 1, -len(rows), sup["id"])

    sections = []
    total_active_rows = 0
    for sup in sorted(suppliers, key=sort_key):
        sec, _has_active, _n, n_active = _supplier_section_html(store, sup, now)
        total_active_rows += n_active
        sections.append(sec)

    unmatched = store.unmatched_exposures()
    per_sup = " · ".join(f"{s}:{c}" for s, c in sorted(result.per_supplier.items()))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija — P1 Supply-chain Credential Exposure</title>
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font: 14px/1.5 -apple-system, Segoe UI, Roboto, sans-serif;
         background: #0e1117; color: #e6edf3; padding: 24px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: #8b949e; margin: 0 0 16px; font-size: 13px; }}
  .guard {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
           padding: 10px 14px; font-size: 12px; color: #8b949e; margin-bottom: 20px; }}
  .kpis {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }}
  .kpi {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px;
         padding: 12px 16px; min-width: 120px; }}
  .kpi .n {{ font-size: 22px; font-weight: 700; }}
  .kpi .l {{ font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: .04em; }}
  .kpi.alert .n {{ color: #ff6b6b; }}
  section.supplier {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
                     padding: 14px 16px; margin-bottom: 16px; }}
  section.has-active {{ border-color: #d1242f; box-shadow: 0 0 0 1px #d1242f33; }}
  h3 {{ margin: 0 0 4px; font-size: 15px; }}
  .sid {{ color: #8b949e; font-weight: 400; font-size: 12px; }}
  .meta, .prop {{ color: #8b949e; font-size: 12px; margin-bottom: 6px; }}
  .prop {{ color: #a5d6ff; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12.5px; }}
  th {{ text-align: left; color: #8b949e; font-weight: 600; border-bottom: 1px solid #30363d;
       padding: 6px 8px; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #21262d; vertical-align: top; }}
  tr.active-row td {{ background: #2d0f12; }}
  tr.devrow td {{ color: #8b949e; font-size: 11px; padding-top: 0; border-bottom: 1px solid #21262d; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .secret {{ color: #d29922; }}
  .ref {{ color: #6e7681; }}
  .badge {{ display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 999px;
           background: #30363d; color: #c9d1d9; vertical-align: middle; }}
  .badge.active {{ background: #d1242f; color: #fff; }}
  .badge.clean {{ background: #238636; color: #fff; }}
  .muted {{ color: #6e7681; }}
  .unmatched {{ background: #161b22; border: 1px dashed #30363d; border-radius: 8px;
               padding: 10px 14px; font-size: 12px; color: #8b949e; margin-top: 8px; }}
</style></head><body>
<h1>Omija — Supply-chain Credential Exposure (P1 vertical slice)</h1>
<p class="sub">registry → mock query → normalize → CorrelateExposure → ontology → screen ·
demo anchor {_fmt_ts(now)} UTC</p>
<div class="guard">SYNTHETIC DEMO — all domains are <code>*.example</code>, no real company is
named or targeted. Secrets are masked (first 2 chars + <code>***</code>); raw secrets never
leave <code>normalize()</code>. Defensive early-warning only — no send, no scanning.</div>
<div class="kpis">
  <div class="kpi"><div class="n">{result.matched_exposures}</div><div class="l">matched exposures</div></div>
  <div class="kpi"><div class="n">{len(result.per_supplier)}</div><div class="l">suppliers hit</div></div>
  <div class="kpi alert"><div class="n">{total_active_rows}</div><div class="l">active signals</div></div>
  <div class="kpi"><div class="n">{len(unmatched)}</div><div class="l">unmatched</div></div>
</div>
<p class="sub">per-supplier matches: {_e(per_sup) or "—"}</p>
{"".join(sections)}
<div class="unmatched"><strong>Unmatched exposures:</strong> {len(unmatched)}
{("— " + ", ".join(_e(u.get("source_ref")) for u in unmatched)) if unmatched else "(none — every exposure attributed to a registered supplier)"}</div>
</body></html>"""


def run() -> int:
    store, result, written = build_store()
    now = DEMO_NOW

    os.makedirs(OUT_DIR, exist_ok=True)
    html_str = build_report_html(store, result, now)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(html_str)

    # CLI summary.
    print("=" * 70)
    print("P1 vertical slice: registry → mock → normalize → correlate → screen")
    print(f"anchor DEMO_NOW = {_fmt_ts(now)} UTC")
    print("=" * 70)
    print(f"records written        : {written}")
    print(f"{result.summary()}")
    print(f"report                 : {OUT_HTML}\n")

    print(f"{'supplier':<20} {'tier':<5} {'exposures':<10} {'active':<7} match")
    print("-" * 70)
    total_active = 0
    for sup in store.suppliers():
        rows = store.exposures_for_supplier(sup["id"])
        active = [r for r in rows if is_active(r, now)]
        total_active += len(active)
        flag = "ACTIVE" if active else ("clean" if not rows else "exposed")
        print(f"{sup['name']:<20} T{sup['tier']:<4} {len(rows):<10} "
              f"{len(active):<7} {flag}")

    unmatched = store.unmatched_exposures()
    # Masking guard: no raw-looking secret should ever be in the HTML output.
    import re
    leaked = re.findall(r"Synthetic-[A-Za-z]+-\d+!|SID[0-9a-f]{20,}", html_str)

    print("-" * 70)
    print(f"unmatched exposures    : {len(unmatched)}")
    print(f"raw secrets in report  : {len(leaked)}  (must be 0)")
    print(f"total active signals   : {total_active}")
    print("=" * 70)

    ok = (written > 0 and result.matched_exposures > 0
          and total_active > 0 and not leaked and os.path.exists(OUT_HTML))
    print("RESULT:", "OK" if ok else "FAIL")
    store.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
