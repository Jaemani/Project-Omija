"""Generate a network-style data coverage map for the steady-state demo."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out"
SEED_DIR = OUT_DIR / "foundry_seed"
PUBLIC_CONTEXT = OUT_DIR / "public_context" / "summary.json"
ACTION_CHAIN = OUT_DIR / "foundry_action_chain.json"
PROGRAM_VIEW = OUT_DIR / "program_threat_view.json"
OUT_HTML = OUT_DIR / "data_coverage_map.html"


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def read_csv_count(name: str) -> int:
    path = SEED_DIR / name
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as fh:
        return max(0, sum(1 for _ in csv.DictReader(fh)))


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload() -> dict[str, Any]:
    public = read_json(PUBLIC_CONTEXT) or {}
    actions = read_json(ACTION_CHAIN) or {}
    program = read_json(PROGRAM_VIEW) or {}
    nvd_total = sum((query.get("total_results") or 0) for query in public.get("nvd", {}).get("queries", []))
    return {
        "seed_counts": {
            "suppliers": read_csv_count("01_supplier.csv"),
            "primes": read_csv_count("02_prime.csv"),
            "programs": read_csv_count("03_program.csv"),
            "domains": read_csv_count("04_domain.csv"),
            "identities": read_csv_count("05_identity.csv"),
            "credential_exposures": read_csv_count("06_credential_exposure.csv"),
            "infected_devices": read_csv_count("07_infected_device.csv"),
            "risk_assessments": read_csv_count("10_risk_assessment.csv"),
            "incidents": read_csv_count("11_compromise_incident.csv"),
            "program_exposures": read_csv_count("12_program_exposure.csv"),
            "drafts": read_csv_count("13_notification_draft.csv"),
        },
        "public_context": {
            "kev_total": public.get("cisa_kev", {}).get("total_vulnerabilities", 0),
            "kev_access": public.get("cisa_kev", {}).get("access_relevant_count", 0),
            "nvd_total": nvd_total,
            "attack_techniques": public.get("mitre_attack", {}).get("selected_count", 0),
            "urlhaus_sample": public.get("urlhaus", {}).get("sampled_rows", 0),
            "hibp_breaches": public.get("hibp", {}).get("breach_count", 0),
        },
        "live_evidence": {
            "action_steps": len(actions.get("steps", [])) if isinstance(actions, dict) else 0,
            "program_chain": len(program.get("chain", [])) if isinstance(program, dict) else 0,
            "cross_org_hits": len(program.get("cross_org_hits", [])) if isinstance(program, dict) else 0,
        },
    }


def stat(label: str, value: Any, tag: str) -> str:
    return f"<div class='stat {e(tag)}'><span>{e(label)}</span><strong>{e(value)}</strong></div>"


def render(payload: dict[str, Any]) -> str:
    seed = payload["seed_counts"]
    public = payload["public_context"]
    live = payload["live_evidence"]
    seed_stats = "".join(
        [
            stat("Suppliers", seed["suppliers"], "seed"),
            stat("Domains", seed["domains"], "seed"),
            stat("Identities", seed["identities"], "seed"),
            stat("Exposure slots", seed["credential_exposures"], "seed"),
            stat("Infected devices", seed["infected_devices"], "seed"),
            stat("Incidents", seed["incidents"], "engine"),
            stat("Programs", seed["programs"], "seed"),
            stat("Drafts", seed["drafts"], "engine"),
        ]
    )
    public_stats = "".join(
        [
            stat("CISA KEV", public["kev_total"], "public"),
            stat("Access-relevant KEV", public["kev_access"], "public"),
            stat("NVD asset queries", public["nvd_total"], "public"),
            stat("ATT&CK techniques", public["attack_techniques"], "public"),
            stat("URLhaus sample", public["urlhaus_sample"], "public"),
            stat("HIBP breach metadata", public["hibp_breaches"], "public"),
        ]
    )
    live_stats = "".join(
        [
            stat("Foundry action readbacks", live["action_steps"], "live"),
            stat("Program reverse chains", live["program_chain"], "engine"),
            stat("Cross-org hits", live["cross_org_hits"], "engine"),
        ]
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Omija Data Coverage Map</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#0d0d0d; --panel:#151514; --panel2:#1c1b19; --line:#34322d;
  --ink:#f0efea; --muted:#aaa79d; --seed:#8b949e; --public:#d6a21d;
  --engine:#2ea043; --live:#58a6ff; --danger:#f85149; --lock:#6e7681;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }}
header {{ padding:18px 22px; border-bottom:1px solid var(--line); background:var(--panel); }}
.kicker {{ font:11px ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--muted); letter-spacing:1.2px; text-transform:uppercase; }}
h1 {{ margin:5px 0 4px; font-size:22px; letter-spacing:0; }}
.sub {{ color:var(--muted); max-width:920px; }}
main {{ padding:18px 22px 42px; display:grid; gap:18px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:8px; }}
.chip {{ border:1px solid var(--line); border-radius:4px; padding:4px 7px; font:11px ui-monospace,SFMono-Regular,Menlo,monospace; }}
.seed {{ color:var(--seed); }} .public {{ color:var(--public); }} .engine {{ color:var(--engine); }} .live {{ color:var(--live); }} .locked {{ color:var(--lock); }}
.grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:13px; }}
.panel h2 {{ margin:0 0 10px; font-size:14px; }}
.stats {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }}
.stat {{ background:var(--panel2); border:1px solid var(--line); border-left:3px solid currentColor; border-radius:6px; padding:8px; min-height:60px; }}
.stat span {{ display:block; color:var(--muted); font-size:11px; }}
.stat strong {{ display:block; margin-top:3px; font:22px ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--ink); }}
.network {{ overflow-x:auto; background:#090909; border:1px solid var(--line); border-radius:8px; }}
svg {{ display:block; min-width:1120px; width:100%; height:auto; }}
.node rect {{ fill:var(--panel2); stroke:var(--line); stroke-width:1.2; rx:8; }}
.node text {{ fill:var(--ink); font-size:12px; font-weight:650; }}
.node .small {{ fill:var(--muted); font-size:10px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:500; }}
.node.seed rect {{ stroke:var(--seed); }} .node.public rect {{ stroke:var(--public); }}
.node.engine rect {{ stroke:var(--engine); }} .node.live rect {{ stroke:var(--live); }}
.node.locked rect {{ stroke:var(--lock); stroke-dasharray:5 4; }}
.edge {{ stroke:#5c5a54; stroke-width:1.4; marker-end:url(#arrow); }}
.edge.public {{ stroke:var(--public); }} .edge.engine {{ stroke:var(--engine); }} .edge.live {{ stroke:var(--live); }}
.caption {{ color:var(--muted); font-size:12px; margin-top:8px; }}
@media (max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} .stats {{ grid-template-columns:1fr 1fr; }} }}
</style>
</head>
<body>
<header>
  <div class="kicker">OMIJA DATA COVERAGE MAP</div>
  <h1>무엇을 어디서 관리하고, 무엇으로 감시하는가</h1>
  <div class="sub">민감 데이터는 잠긴 슬롯으로 두고, synthetic seed · 공개 컨텍스트 · 실제 엔진 산출 · Foundry readback을 구분해 보여주는 평시 운영 지도.</div>
</header>
<main>
  <div class="legend">
    <span class="chip seed">SEED synthetic entity</span>
    <span class="chip public">PUBLIC_CONTEXT open data</span>
    <span class="chip engine">ENGINE computed decision</span>
    <span class="chip live">LIVE Foundry/readback</span>
    <span class="chip locked">LOCKED sensitive slot</span>
  </div>

  <section class="network">
  <svg viewBox="0 0 1120 520" role="img" aria-label="Omija data coverage network">
    <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#5c5a54"/></marker></defs>
    <line class="edge seed" x1="180" y1="105" x2="370" y2="105"/>
    <line class="edge seed" x1="180" y1="185" x2="370" y2="185"/>
    <line class="edge locked" x1="180" y1="285" x2="370" y2="285"/>
    <line class="edge public" x1="180" y1="390" x2="370" y2="390"/>
    <line class="edge engine" x1="545" y1="105" x2="725" y2="165"/>
    <line class="edge engine" x1="545" y1="185" x2="725" y2="245"/>
    <line class="edge engine" x1="545" y1="285" x2="725" y2="245"/>
    <line class="edge public" x1="545" y1="390" x2="725" y2="325"/>
    <line class="edge live" x1="880" y1="165" x2="1040" y2="165"/>
    <line class="edge engine" x1="880" y1="245" x2="1040" y2="245"/>
    <line class="edge engine" x1="880" y1="325" x2="1040" y2="325"/>

    <g class="node seed"><rect x="30" y="70" width="150" height="70"/><text x="48" y="100">Foundry seed CSV</text><text x="48" y="120" class="small">suppliers/domains/programs</text></g>
    <g class="node seed"><rect x="30" y="150" width="150" height="70"/><text x="48" y="180">Synthetic corpus</text><text x="48" y="200" class="small">exposure/device slots</text></g>
    <g class="node locked"><rect x="30" y="250" width="150" height="70"/><text x="48" y="280">Credential feed</text><text x="48" y="300" class="small">locked / not queried</text></g>
    <g class="node public"><rect x="30" y="355" width="150" height="70"/><text x="48" y="385">Open context</text><text x="48" y="405" class="small">KEV/NVD/ATT&CK/HIBP</text></g>

    <g class="node seed"><rect x="370" y="70" width="175" height="70"/><text x="390" y="100">Ontology objects</text><text x="390" y="120" class="small">Supplier Domain Identity</text></g>
    <g class="node seed"><rect x="370" y="150" width="175" height="70"/><text x="390" y="180">Evidence slots</text><text x="390" y="200" class="small">Exposure Device Source</text></g>
    <g class="node locked"><rect x="370" y="250" width="175" height="70"/><text x="390" y="280">Sensitive review</text><text x="390" y="300" class="small">masked / gated / audited</text></g>
    <g class="node public"><rect x="370" y="355" width="175" height="70"/><text x="390" y="385">Context components</text><text x="390" y="405" class="small">asset risk, techniques</text></g>

    <g class="node engine"><rect x="725" y="130" width="155" height="70"/><text x="745" y="160">RiskAssessment</text><text x="745" y="180" class="small">band + score</text></g>
    <g class="node engine"><rect x="725" y="210" width="155" height="70"/><text x="745" y="240">CompromiseIncident</text><text x="745" y="260" class="small">traverses path</text></g>
    <g class="node engine"><rect x="725" y="290" width="155" height="70"/><text x="745" y="320">ProgramExposure</text><text x="745" y="340" class="small">blast radius rollup</text></g>

    <g class="node live"><rect x="950" y="130" width="145" height="70"/><text x="970" y="160">Steady console</text><text x="970" y="180" class="small">coverage + quiet proof</text></g>
    <g class="node engine"><rect x="950" y="210" width="145" height="70"/><text x="970" y="240">Incident report</text><text x="970" y="260" class="small">when path active</text></g>
    <g class="node engine"><rect x="950" y="290" width="145" height="70"/><text x="970" y="320">Program view</text><text x="970" y="340" class="small">reverse query</text></g>
  </svg>
  </section>

  <div class="grid">
    <section class="panel"><h2>Managed synthetic structure</h2><div class="stats">{seed_stats}</div></section>
    <section class="panel"><h2>Open public context</h2><div class="stats">{public_stats}</div></section>
    <section class="panel"><h2>Engine / live evidence</h2><div class="stats">{live_stats}</div><div class="caption">Foundry action readbacks and reverse-query outputs prove the operating workflow; credential-feed slots remain locked.</div></section>
  </div>
</main>
</body>
</html>"""


def main() -> int:
    payload = build_payload()
    OUT_HTML.write_text(render(payload), encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
