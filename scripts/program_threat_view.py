"""Program-centric threat view — the SAME ontology, queried in REVERSE.

PropagateRisk (P3/actions/propagate_risk.py) walks FORWARD: Supplier -> Prime ->
Program, rolling supplier-level risk UP onto a defense Program. This script asks
the identical graph in the OPPOSITE direction, starting from a Program:

    Program -> which Primes/Suppliers feed it (reverse-walking
               subcontractsTo*/supplies/runs, variable depth)
            -> which of those carry an open CompromiseIncident / RiskAssessment
               right now, plus any CredentialExposure whose `targets` edge hits
               an asset owned by a Prime that runs this Program — even if the
               exposure's own Supplier is elsewhere in (or entirely outside) the
               chain (ontology.md §0: of != targets, the cross-org signal).

같은 온톨로지, 반대 방향 질의 — 협력사 관점과 프로그램 관점이 동일 그래프에서 나온다.

Backends:
  --backend local    (default) full mock pipe on an in-memory SQLite store —
                      ALWAYS works offline (registry -> mock -> correlate ->
                      resolve -> flag -> score -> propagate).
  --backend foundry   read the published Foundry ontology via OSDK. Skips
                      gracefully with a clear message if FOUNDRY_OSDK_MODULE /
                      FOUNDRY_OSDK_CLIENT are not configured
                      (store/osdk_compat.py build_client_from_env).

Output: CLI table + out/program_threat_view.json + out/program_threat_view.html
(self-contained, dark theme, Korean captions / English API names). No network
beyond the optional OSDK read. No StealthMole mentions.

Run:
  uv run python scripts/program_threat_view.py
  uv run python scripts/program_threat_view.py prog-harbor
  uv run python scripts/program_threat_view.py prog-sentinel --backend foundry
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
sys.path.insert(0, str(REPO_ROOT))

from actions.propagate_risk import propagate_program_risk  # noqa: E402
from adapter.mock import DEMO_NOW  # noqa: E402
from scripts.omija_style import nav_strip  # noqa: E402
from scripts.p5_drafts import build_pipeline  # noqa: E402
from store.osdk_compat import OsdkError  # noqa: E402

CAPTION = "같은 온톨로지, 반대 방향 질의 — 협력사 관점과 프로그램 관점이 동일 그래프에서 나온다."
DEFAULT_PROGRAM = "prog-sentinel"

OUT_JSON = OUT_DIR / "program_threat_view.json"
OUT_HTML = OUT_DIR / "program_threat_view.html"


class ThreatViewStore(Protocol):
    def suppliers(self) -> list[dict[str, Any]]: ...
    def programs(self) -> list[dict[str, Any]]: ...
    def propagation_paths(self, supplier_id: str, *, depth_cap: int = 6) -> list[list[dict[str, Any]]]: ...
    def exposures_for_supplier(self, supplier_id: str) -> list[dict[str, Any]]: ...
    def all_exposures(self) -> list[dict[str, Any]]: ...
    def incidents_for_supplier(self, supplier_id: str) -> list[dict[str, Any]]: ...
    def risk_assessments(self) -> list[dict[str, Any]]: ...
    def risk_evidence(self, assessment_ref: str) -> list[dict[str, Any]]: ...
    def program_exposures(self) -> list[dict[str, Any]]: ...
    def program_exposure_evidence(self, exposure_ref: str) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
# Reverse traversal — Program -> contributing Supplier/Prime chain
# ---------------------------------------------------------------------------

def contributing_chain(store: ThreatViewStore, program_id: str) -> list[dict[str, Any]]:
    """Reverse-walk the SAME forward edges PropagateRisk walks
    (subcontractsTo* -> supplies -> runs): for every Supplier, check whether one
    of its variable-depth propagation paths lands on `program_id`. depth=0 means
    the supplier itself `supplies` the Prime that `runs` the program; depth>0
    means N subcontractsTo hops sit below the supplier that does (the 2차/3차
    multi-tier case). One row per supplier — the shallowest depth wins if a
    supplier reaches the program more than one way (diamond chain)."""
    best: dict[str, dict[str, Any]] = {}
    for supplier in store.suppliers():
        sid = supplier["id"]
        for path in store.propagation_paths(sid):
            if not path or path[-1].get("ref") != program_id:
                continue
            supplier_nodes = [n for n in path if n.get("type") == "Supplier"]
            prime_node = next((n for n in path if n.get("type") == "Prime"), None)
            depth = len(supplier_nodes) - 1  # 0 = direct supplier -> prime
            cur = best.get(sid)
            if cur is not None and cur["depth"] <= depth:
                continue
            exposures = store.exposures_for_supplier(sid)
            incidents = store.incidents_for_supplier(sid)
            best[sid] = {
                "supplier_id": sid,
                "supplier_name": supplier.get("name", sid),
                "depth": depth,
                "prime_ref": prime_node["ref"] if prime_node else None,
                "prime_name": prime_node.get("name") if prime_node else None,
                "chain": " -> ".join(
                    f"{n['type']}({n.get('name') or n.get('ref')})" for n in path
                ),
                "exposure_count": len(exposures),
                "has_active_incident": bool(incidents),
            }
    return sorted(best.values(), key=lambda e: (e["depth"], e["supplier_id"]))


def collect_incidents(
    store: ThreatViewStore, chain: list[dict[str, Any]], program_id: str
) -> list[dict[str, Any]]:
    """Open CompromiseIncidents whose blast radius reaches `program_id`, sourced
    from every contributing supplier (band-on-top: incidents are always the
    highest-severity row in this view)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in chain:
        for inc in store.incidents_for_supplier(entry["supplier_id"]):
            if inc["id"] in seen:
                continue
            # blast_radius["programs"] is a list of {"ref","name"} dicts
            # (actions/flag_active.py._blast_radius), not bare ids.
            blast_programs = inc.get("blast_radius", {}).get("programs", [])
            program_refs = {
                p.get("ref") if isinstance(p, dict) else p for p in blast_programs
            }
            if program_id in program_refs:
                seen.add(inc["id"])
                out.append(inc)
    return out


def collect_risk(store: ThreatViewStore, chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """RiskAssessments of every contributing supplier, active-on-top (score
    desc — the same active-floor/base-cap dominance invariant as P3)."""
    ids = {e["supplier_id"] for e in chain}
    out = []
    for ra in store.risk_assessments():
        if ra.get("supplier_ref") in ids:
            out.append({**ra, "evidence": store.risk_evidence(ra["id"])})
    return sorted(out, key=lambda r: -(r.get("score") or 0))


def collect_cross_org(
    store: ThreatViewStore, chain: list[dict[str, Any]], prime_refs: set[str]
) -> list[dict[str, Any]]:
    """CredentialExposures whose `targets` edge differs from the exposure's own
    `of -> belongs_to` domain (ontology.md §0: of != targets).

    Two precision levels, because the two backends carry different amounts of
    structural detail today:
      - "exact": the store exposes `target_prime_ref`/`cross_org_target`
        (SqliteOntologyStore's `prime_domain` table — store/sqlite.py) so we
        can confirm the target Domain is owned by a Prime that runs THIS
        program. Reported regardless of whether the owning supplier is itself
        in the contributing chain — the asset being targeted is what matters.
      - "heuristic": the backend (e.g. FoundryOntologyStore, which has no
        Prime-owns-Domain read method wired yet) only carries
        `target_domain_ref` with no prime attribution. We still surface a
        domain_ref != target_domain_ref mismatch as a candidate cross-org
        signal, but only for suppliers already confirmed in the contributing
        chain (so it stays a load-bearing signal, not a guess) and label it
        clearly as unverified prime-ownership.
    """
    ids = {e["supplier_id"] for e in chain}
    has_prime_field = any("target_prime_ref" in row for row in store.all_exposures())
    hits = []
    for row in store.all_exposures():
        owner_domain = row.get("domain_ref")
        target_domain = row.get("target_domain_ref")
        if not target_domain or target_domain == owner_domain:
            continue
        if has_prime_field:
            if not row.get("cross_org_target"):
                continue
            if row.get("target_prime_ref") not in prime_refs:
                continue
            precision = "exact"
        else:
            if row.get("supplier_id") not in ids:
                continue
            precision = "heuristic (no prime-owns-domain data on this backend)"
        hits.append({
            "id": row.get("id"),
            "identity_ref": row.get("identity_ref"),
            "owner_supplier": row.get("supplier_id"),
            "owner_domain": owner_domain,
            "target_domain": target_domain,
            "target_prime": row.get("target_prime_ref"),
            "source_ref": row.get("source_ref"),
            "in_supply_chain": row.get("supplier_id") in ids,
            "precision": precision,
        })
    return hits


def program_exposure_summary(store: ThreatViewStore, program_id: str) -> dict[str, Any] | None:
    """The already-computed FORWARD rollup (PropagateRisk's ProgramExposure), if
    one exists — shown alongside the reverse view as a cross-check: same graph,
    same program, two directions of query, one answer."""
    for pe in store.program_exposures():
        if pe.get("program_ref") == program_id:
            return {**pe, "evidence": store.program_exposure_evidence(pe["id"])}
    return None


def build_view(store: ThreatViewStore, program_id: str) -> dict[str, Any]:
    programs = {p["id"]: p for p in store.programs()}
    program = programs.get(program_id)
    if program is None:
        raise SystemExit(
            f"program not found: {program_id!r} (known: {sorted(programs)})"
        )

    chain = contributing_chain(store, program_id)
    prime_refs = {e["prime_ref"] for e in chain if e.get("prime_ref")}
    incidents = collect_incidents(store, chain, program_id)
    risk = collect_risk(store, chain)
    cross_org = collect_cross_org(store, chain, prime_refs)
    pexp = program_exposure_summary(store, program_id)

    return {
        "caption": CAPTION,
        "program": program,
        "chain": chain,
        "primes": sorted(prime_refs),
        "incidents": incidents,
        "risk_assessments": risk,
        "cross_org_hits": cross_org,
        "program_exposure": pexp,
    }


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def run_local(program_id: str) -> dict[str, Any]:
    store, _assessments = build_pipeline(DEMO_NOW)
    try:
        propagate_program_risk(store, now=DEMO_NOW)
        return build_view(store, program_id)
    finally:
        store.close()


def run_foundry(program_id: str) -> dict[str, Any] | None:
    from store.foundry import FoundryOntologyStore  # noqa: E402 (lazy: OSDK optional)

    store = FoundryOntologyStore()
    try:
        return build_view(store, program_id)
    except OsdkError as exc:
        print(f"[foundry] skipped — OSDK not configured: {exc}")
        return None
    finally:
        close = getattr(store, "close", None)
        if close:
            close()


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------

def print_view(view: dict[str, Any], *, backend: str) -> None:
    program = view["program"]
    print("=" * 78)
    print("PROGRAM THREAT VIEW — reverse query (Program -> contributing supply chain)")
    print(f"backend={backend}  program={program.get('name')} ({program['id']})  "
          f"sensitivity={program.get('sensitivity')}")
    print("=" * 78)
    print(f"caption: {view['caption']}")
    print()

    print(f"{'depth':<6}{'supplier':<24}{'prime':<20}{'exposures':<10}{'active'}")
    print("-" * 78)
    for e in view["chain"]:
        print(
            f"{e['depth']:<6}{e['supplier_name']:<24}{(e['prime_name'] or '-'):<20}"
            f"{e['exposure_count']:<10}{'YES' if e['has_active_incident'] else '-'}"
        )
    if not view["chain"]:
        print("(no supplier reaches this program)")

    print()
    print("Active incidents reaching this program (band on top):")
    if view["incidents"]:
        for inc in view["incidents"]:
            print(f"  {inc['id']:<24} supplier={inc.get('supplier_ref')}  "
                  f"opened={inc.get('opened_at')}  status={inc.get('status')}")
    else:
        print("  (none)")

    print()
    print("Risk assessments (contributing suppliers, active-on-top):")
    for ra in view["risk_assessments"]:
        ev_refs = ", ".join(e["evidence_ref"] for e in ra.get("evidence", [])) or "-"
        print(f"  {ra.get('supplier_ref'):<10} score={ra.get('score'):<7}"
              f"grade={ra.get('grade'):<4} active={ra.get('active_flag')}  ev=[{ev_refs}]")

    print()
    print("Cross-org targets hits (of != targets; asset owned by a prime that runs this program):")
    if view["cross_org_hits"]:
        for hit in view["cross_org_hits"]:
            print(f"  {hit['id']:<32} owner={hit['owner_supplier']}({hit['owner_domain']})  "
                  f"target={hit['target_domain']}({hit['target_prime']})  "
                  f"in_chain={hit['in_supply_chain']}  precision={hit['precision']}  "
                  f"ref={hit['source_ref']}")
    else:
        print("  (none)")

    print()
    pexp = view.get("program_exposure")
    if pexp:
        ev_refs = ", ".join(e["evidence_ref"] for e in pexp.get("evidence", [])) or "-"
        print("ProgramExposure rollup (PropagateRisk, forward direction — cross-check):")
        print(f"  score={pexp.get('score')} grade={pexp.get('grade')} "
              f"active={pexp.get('active_flag')}  ev=[{ev_refs}]")
    else:
        print("ProgramExposure rollup: (none — no evidence to persist yet, per provenance rule)")
    print("=" * 78)


def write_json(view: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(view, indent=2, ensure_ascii=False), encoding="utf-8")
    return OUT_JSON


# ---------------------------------------------------------------------------
# HTML (self-contained, dark theme — CSS variables lifted from palantir_v1.html)
# ---------------------------------------------------------------------------

def _e(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def _band_class(grade: str | None) -> str:
    return {"즉시": "band-a", "주의": "band-b"}.get(grade or "", "band-c")


def render_html(view: dict[str, Any], *, backend: str) -> str:
    program = view["program"]
    chain_rows = "".join(
        f'<tr class="{"hot" if e["has_active_incident"] else ""}">'
        f'<td class="mono">{e["depth"]}</td>'
        f'<td>{_e(e["supplier_name"])} <span class="ref">{_e(e["supplier_id"])}</span></td>'
        f'<td>{_e(e["prime_name"]) or "&mdash;"}</td>'
        f'<td class="mono">{e["exposure_count"]}</td>'
        f'<td>{"<span class=\'dot band-a\'></span> ACTIVE" if e["has_active_incident"] else "&mdash;"}</td>'
        f'<td class="ref mono" title="{_e(e["chain"])}">{_e(e["chain"][:64])}{"…" if len(e["chain"]) > 64 else ""}</td>'
        "</tr>"
        for e in view["chain"]
    ) or '<tr><td colspan="6" class="muted">no supplier reaches this program</td></tr>'

    incident_rows = "".join(
        f'<tr class="band-a-row">'
        f'<td><span class="dot band-a"></span>{_e(inc["id"])}</td>'
        f'<td>{_e(inc.get("supplier_ref"))}</td>'
        f'<td>{_e(inc.get("status"))}</td>'
        f'<td class="mono">{_e(inc.get("opened_at"))}</td>'
        f'<td class="ref mono">{_e(inc["id"])}</td>'
        "</tr>"
        for inc in view["incidents"]
    ) or '<tr><td colspan="5" class="muted">none</td></tr>'

    risk_rows = "".join(
        f'<tr class="{_band_class(ra.get("grade"))}-row">'
        f'<td><span class="dot {_band_class(ra.get("grade"))}"></span>{_e(ra.get("supplier_ref"))}</td>'
        f'<td class="mono">{ra.get("score")}</td>'
        f'<td>{_e(ra.get("grade"))}</td>'
        f'<td>{"YES" if ra.get("active_flag") else "&mdash;"}</td>'
        f'<td class="ref mono">{_e(", ".join(e["evidence_ref"] for e in ra.get("evidence", [])) or "&mdash;")}</td>'
        "</tr>"
        for ra in view["risk_assessments"]
    ) or '<tr><td colspan="5" class="muted">none</td></tr>'

    cross_rows = "".join(
        f'<tr class="cross-row">'
        f'<td class="mono">{_e(hit["id"])}</td>'
        f'<td>{_e(hit["owner_supplier"])} <span class="ref">({_e(hit["owner_domain"])})</span></td>'
        f'<td><span class="cross-arrow">targets &rarr;</span> {_e(hit["target_domain"])} '
        f'<span class="ref">({_e(hit["target_prime"])})</span></td>'
        f'<td>{"in-chain" if hit["in_supply_chain"] else "OUTSIDE chain"}'
        f'<div class="ref">{_e(hit["precision"])}</div></td>'
        f'<td class="ref mono">{_e(hit["source_ref"])}</td>'
        "</tr>"
        for hit in view["cross_org_hits"]
    ) or '<tr><td colspan="5" class="muted">none</td></tr>'

    pexp = view.get("program_exposure")
    if pexp:
        pexp_html = (
            f'<div class="pexp {_band_class(pexp.get("grade"))}">'
            f'<b>ProgramExposure</b> (forward rollup, cross-check) — '
            f'score={_e(pexp.get("score"))} grade={_e(pexp.get("grade"))} '
            f'active={"YES" if pexp.get("active_flag") else "no"} '
            f'ev=[{_e(", ".join(e["evidence_ref"] for e in pexp.get("evidence", [])))}]'
            f'</div>'
        )
    else:
        pexp_html = '<div class="pexp band-c">no ProgramExposure yet (provenance rule: no evidence, no object)</div>'

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija · Program Threat View</title>
<style>
:root{{
  --plane:#0d0d0d; --surface:#141413; --surface-2:#1a1a19; --raised:#201f1d;
  --ink:#ececea; --ink-2:#a9a89f; --muted:#6f6e68;
  --hair:#262624; --hair-2:#35342f;
  --c-entity:#3987e5; --c-evidence:#199e70; --c-derived:#c98500; --c-output:#9085e9;
  --cross:#ec835a;
  --band-a:#d03b3b; --band-b:#fab219; --band-c:#3987e5;
  --mono:ui-monospace,SFMono-Regular,Menlo,"Cascadia Code",monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--plane);color:var(--ink);font-family:var(--sans);
  font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}}
body{{padding:0 0 28px}}
.mono{{font-family:var(--mono)}}
.scroll-x{{overflow-x:auto}}
.topbar{{display:flex;align-items:center;gap:14px;padding:12px 20px;
  border-bottom:1px solid var(--hair);background:var(--surface);position:sticky;top:0}}
.topbar .brand{{font-family:var(--mono);font-size:12px;letter-spacing:1.5px;
  text-transform:uppercase}}
.topbar .ver{{font-family:var(--mono);font-size:11px;color:var(--muted);
  border:1px solid var(--hair-2);border-radius:3px;padding:2px 7px}}
.hero{{padding:16px 20px;border-bottom:1px solid var(--hair);background:var(--surface-2)}}
.hero h1{{margin:0 0 4px;font-size:18px;font-weight:600}}
.hero .sub{{color:var(--ink-2);font-size:12.5px}}
.caption{{margin-top:10px;padding:9px 12px;border-left:2px solid var(--c-output);
  background:rgba(144,133,233,.08);border-radius:0 5px 5px 0;font-size:13px;color:var(--ink)}}
main{{padding:18px 20px;display:flex;flex-direction:column;gap:22px}}
.lbl{{font-family:var(--mono);font-size:10.5px;letter-spacing:1px;color:var(--muted);
  text-transform:uppercase;margin-bottom:8px;display:block}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--surface);
  border:1px solid var(--hair-2);border-radius:6px;overflow:hidden}}
th{{text-align:left;font-weight:600;color:var(--ink-2);background:var(--surface-2);
  padding:7px 10px;border-bottom:1px solid var(--hair);font-size:11px;
  text-transform:uppercase;letter-spacing:.4px}}
td{{padding:7px 10px;border-top:1px solid var(--hair);vertical-align:top}}
tr.hot,tr.band-a-row{{background:rgba(208,59,59,.08)}}
tr.band-b-row{{background:rgba(250,178,25,.06)}}
tr.band-c-row{{background:transparent}}
tr.cross-row{{background:rgba(236,131,90,.08)}}
.ref{{color:var(--muted);font-size:11px}}
.muted{{color:var(--muted);text-align:center;padding:14px}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:6px}}
.band-a{{background:var(--band-a);box-shadow:0 0 6px var(--band-a)}}
.band-b{{background:var(--band-b)}}
.band-c{{background:var(--band-c)}}
.cross-arrow{{color:var(--cross);font-family:var(--mono);font-size:11px}}
.pexp{{padding:9px 12px;border-radius:6px;border:1px solid var(--hair-2);font-size:12.5px;
  background:var(--surface)}}
.pexp.band-a{{border-color:rgba(208,59,59,.5)}}
.pexp.band-b{{border-color:rgba(250,178,25,.5)}}
.footer{{padding:14px 20px;border-top:1px solid var(--hair);color:var(--muted);
  font-size:11px;font-family:var(--mono)}}
</style></head>
<body>
{nav_strip("program_threat_view.html")}
<div class="topbar">
  <span class="brand">OMIJA · SUPPLY-CHAIN CREDENTIAL EXPOSURE</span>
  <span class="ver">PROGRAM THREAT VIEW · backend={_e(backend)}</span>
</div>
<div class="hero">
  <h1>{_e(program.get("name"))} <span class="ref">{_e(program["id"])}</span></h1>
  <div class="sub">sensitivity={_e(program.get("sensitivity"))} &middot;
    reverse query: Program &rarr; contributing Supplier/Prime chain &rarr; open incidents /
    risk / cross-org exposure</div>
  <div class="caption">{_e(view["caption"])}</div>
</div>
<main>
  <section class="scroll-x">
    <span class="lbl">Contributing supply chain (reverse-walked subcontractsTo* &rarr; supplies &rarr; runs)</span>
    <table><thead><tr><th>depth</th><th>supplier</th><th>prime</th><th>exposures</th>
      <th>active</th><th>path</th></tr></thead>
      <tbody>{chain_rows}</tbody></table>
  </section>

  <section class="scroll-x">
    <span class="lbl">Active incidents reaching this program (band on top)</span>
    <table><thead><tr><th>incident</th><th>supplier</th><th>status</th><th>opened</th>
      <th>evidence ref</th></tr></thead>
      <tbody>{incident_rows}</tbody></table>
  </section>

  <section class="scroll-x">
    <span class="lbl">Risk assessments — contributing suppliers, active-on-top</span>
    <table><thead><tr><th>supplier</th><th>score</th><th>grade</th><th>active</th>
      <th>evidence ref</th></tr></thead>
      <tbody>{risk_rows}</tbody></table>
  </section>

  <section class="scroll-x">
    <span class="lbl">Cross-org targets hits (of &ne; targets — asset owned by a prime running this program)</span>
    <table><thead><tr><th>exposure</th><th>owner (of)</th><th>target (targets)</th>
      <th>chain membership</th><th>evidence ref</th></tr></thead>
      <tbody>{cross_rows}</tbody></table>
  </section>

  <section>
    <span class="lbl">Forward cross-check (PropagateRisk ProgramExposure)</span>
    {pexp_html}
  </section>
</main>
<div class="footer">SYNTHETIC DEMO — every id is *.example / fictional (sup-*, prime-*, prog-*).
No real organization is named or targeted. Read-only reverse query over the SAME ontology
objects PropagateRisk already writes forward &mdash; no new object types, no renamed links.</div>
</body></html>"""


def write_html(view: dict[str, Any], *, backend: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(view, backend=backend), encoding="utf-8")
    return OUT_HTML


# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", nargs="?", default=DEFAULT_PROGRAM)
    parser.add_argument("--backend", choices=("local", "foundry"), default="local")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.backend == "foundry":
        view = run_foundry(args.program)
        if view is None:
            print("RESULT: SKIP (foundry backend not configured — local backend "
                  "always works offline: `uv run python scripts/program_threat_view.py "
                  f"{args.program}`)")
            return 0
    else:
        view = run_local(args.program)

    print_view(view, backend=args.backend)
    out_json = write_json(view)
    out_html = write_html(view, backend=args.backend)
    print(f"json written : {out_json.relative_to(REPO_ROOT)}")
    print(f"html written : {out_html.relative_to(REPO_ROOT)}")

    ok = bool(view["chain"])
    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
