"""Generate a safe input-provider-to-ontology role map page."""

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
OUT_HTML = OUT_DIR / "stealthmole_role_map.html"


def e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def read_csv_count(filename: str) -> int:
    path = SEED_DIR / filename
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_payload() -> dict[str, Any]:
    public = read_json(PUBLIC_CONTEXT)
    nvd_queries = public.get("nvd", {}).get("queries", [])
    nvd_total = sum(query.get("total_results", 0) for query in nvd_queries)
    return {
        "seed": {
            "suppliers": read_csv_count("01_supplier.csv"),
            "domains": read_csv_count("04_domain.csv"),
            "identities": read_csv_count("05_identity.csv"),
            "exposures": read_csv_count("06_credential_exposure.csv"),
            "devices": read_csv_count("07_infected_device.csv"),
            "sources": read_csv_count("08_threat_source.csv"),
            "risks": read_csv_count("10_risk_assessment.csv"),
            "incidents": read_csv_count("11_compromise_incident.csv"),
            "program_exposures": read_csv_count("12_program_exposure.csv"),
            "drafts": read_csv_count("13_notification_draft.csv"),
        },
        "public": {
            "kev_access": public.get("cisa_kev", {}).get("access_relevant_count", 0),
            "attack": public.get("mitre_attack", {}).get("selected_count", 0),
            "nvd_total": nvd_total,
            "urlhaus_tagged": public.get("urlhaus", {}).get("stealer_or_loader_count", 0),
            "hibp": public.get("hibp", {}).get("breach_count", 0),
            "generated_at": public.get("generated_at", "not generated"),
        },
    }


def stat(label: str, value: Any, tone: str) -> str:
    return (
        f"<div class='stat {e(tone)}'>"
        f"<span>{e(label)}</span>"
        f"<strong>{e(value)}</strong>"
        "</div>"
    )


def module_card(title: str, code: str, role: str, object_name: str, emphasis: str) -> str:
    return f"""
    <section class="module">
      <div class="module-top">
        <span class="code">{e(code)}</span>
        <h3>{e(title)}</h3>
      </div>
      <p>{e(role)}</p>
      <div class="maps-to">maps to <strong>{e(object_name)}</strong></div>
      <div class="emphasis">{e(emphasis)}</div>
    </section>
    """


def render(payload: dict[str, Any]) -> str:
    seed = payload["seed"]
    public = payload["public"]
    seed_stats = "".join(
        [
            stat("Suppliers", seed["suppliers"], "seed"),
            stat("Domains", seed["domains"], "seed"),
            stat("Identities", seed["identities"], "seed"),
            stat("Exposure records", seed["exposures"], "seed"),
            stat("Infected devices", seed["devices"], "seed"),
            stat("Threat sources", seed["sources"], "seed"),
        ]
    )
    decision_stats = "".join(
        [
            stat("Risk assessments", seed["risks"], "engine"),
            stat("Incidents", seed["incidents"], "engine"),
            stat("Program exposures", seed["program_exposures"], "engine"),
            stat("Notification drafts", seed["drafts"], "engine"),
        ]
    )
    public_stats = "".join(
        [
            stat("Access-relevant KEV", public["kev_access"], "public"),
            stat("NVD asset query hits", public["nvd_total"], "public"),
            stat("ATT&CK techniques", public["attack"], "public"),
            stat("URLhaus tagged sample", public["urlhaus_tagged"], "public"),
            stat("HIBP breach metadata", public["hibp"], "public"),
        ]
    )
    modules = "".join(
        [
            module_card(
                "Credential Lookout",
                "CL",
                "Domain-based leaked-account signal. It starts the question of whose identity appeared.",
                "CredentialExposure",
                "Useful only after Omija separates account owner (`of`) from target asset (`targets`).",
            ),
            module_card(
                "Compromised Data Set",
                "CDS",
                "Infostealer-derived device signal. It can carry active-risk hints such as recency, session material, and account class.",
                "InfectedDevice",
                "This is the escalation input for active compromise, not a raw table for display.",
            ),
            module_card(
                "Darkweb Tracker",
                "DT",
                "Forum and marketplace context around supplier names, assets, or campaign terms.",
                "ThreatSource",
                "Used as provenance and context; it should not override graph path evidence.",
            ),
            module_card(
                "Telegram Tracker",
                "TT",
                "Channel-based leak and trade context that can corroborate repeated mentions.",
                "ThreatSource",
                "Strengthens source diversity while staying behind review and masking boundaries.",
            ),
        ]
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Omija Input Role Map</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg:#0b0c0d;
      --panel:#151719;
      --panel2:#1c2024;
      --line:#333942;
      --ink:#f2f4f8;
      --muted:#aeb7c2;
      --seed:#9aa4b2;
      --vendor:#58a6ff;
      --public:#d6a21d;
      --engine:#2ea043;
      --decision:#b779ff;
      --lock:#f85149;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:var(--bg);
      color:var(--ink);
      font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;
    }}
    header {{
      padding:18px 22px;
      border-bottom:1px solid var(--line);
      background:linear-gradient(180deg,#171a1e,#111315);
    }}
    .kicker {{
      color:var(--muted);
      font:11px ui-monospace,SFMono-Regular,Menlo,monospace;
      letter-spacing:1px;
      text-transform:uppercase;
    }}
    h1 {{ margin:5px 0 4px; font-size:23px; letter-spacing:0; }}
    h2 {{ margin:0 0 10px; font-size:14px; letter-spacing:0; }}
    h3 {{ margin:0; font-size:15px; letter-spacing:0; }}
    p {{ margin:0; color:var(--muted); }}
    .sub {{ max-width:980px; color:var(--muted); }}
    main {{ padding:18px 22px 42px; display:grid; gap:18px; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .chip {{
      border:1px solid var(--line);
      border-radius:4px;
      padding:4px 7px;
      font:11px ui-monospace,SFMono-Regular,Menlo,monospace;
      background:#101214;
    }}
    .vendor {{ color:var(--vendor); }}
    .seed {{ color:var(--seed); }}
    .public {{ color:var(--public); }}
    .engine {{ color:var(--engine); }}
    .decision {{ color:var(--decision); }}
    .locked {{ color:var(--lock); }}
    .grid {{ display:grid; grid-template-columns:1.15fr .85fr; gap:14px; }}
    .panel {{
      background:var(--panel);
      border:1px solid var(--line);
      border-radius:8px;
      padding:14px;
    }}
    .modules {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    .module {{
      min-height:205px;
      padding:12px;
      border:1px solid var(--line);
      border-top:3px solid var(--vendor);
      border-radius:7px;
      background:var(--panel2);
      display:grid;
      gap:10px;
      align-content:start;
    }}
    .module-top {{ display:flex; align-items:center; gap:8px; }}
    .code {{
      display:inline-grid;
      place-items:center;
      width:36px;
      height:30px;
      border-radius:5px;
      color:var(--vendor);
      border:1px solid color-mix(in srgb, var(--vendor) 55%, var(--line));
      font:12px ui-monospace,SFMono-Regular,Menlo,monospace;
      font-weight:700;
    }}
    .maps-to {{
      color:var(--ink);
      border-left:2px solid var(--engine);
      padding-left:8px;
      font:12px ui-monospace,SFMono-Regular,Menlo,monospace;
    }}
    .emphasis {{ color:var(--muted); font-size:12px; }}
    .network {{
      overflow-x:auto;
      background:#090a0b;
      border:1px solid var(--line);
      border-radius:8px;
    }}
    svg {{ min-width:1120px; width:100%; height:auto; display:block; }}
    .node rect {{ fill:var(--panel2); stroke:var(--line); stroke-width:1.2; rx:8; }}
    .node text {{ fill:var(--ink); font-weight:650; font-size:12px; }}
    .node .small {{ fill:var(--muted); font:10px ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:500; }}
    .node.vendor rect {{ stroke:var(--vendor); }}
    .node.seed rect {{ stroke:var(--seed); }}
    .node.public rect {{ stroke:var(--public); }}
    .node.engine rect {{ stroke:var(--engine); }}
    .node.decision rect {{ stroke:var(--decision); }}
    .node.locked rect {{ stroke:var(--lock); stroke-dasharray:5 4; }}
    .edge {{ fill:none; stroke:#59616c; stroke-width:1.5; marker-end:url(#arrow); }}
    .edge.vendor {{ stroke:var(--vendor); }}
    .edge.public {{ stroke:var(--public); }}
    .edge.engine {{ stroke:var(--engine); }}
    .edge.decision {{ stroke:var(--decision); }}
    .edge.locked {{ stroke:var(--lock); stroke-dasharray:5 5; }}
    .stats {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }}
    .stat {{
      min-height:58px;
      padding:9px;
      border:1px solid var(--line);
      border-left:3px solid currentColor;
      border-radius:6px;
      background:var(--panel2);
    }}
    .stat span {{ display:block; color:var(--muted); font-size:11px; }}
    .stat strong {{ display:block; margin-top:3px; color:var(--ink); font:18px ui-monospace,SFMono-Regular,Menlo,monospace; }}
    .rules {{ display:grid; gap:8px; }}
    .rule {{
      display:grid;
      grid-template-columns:145px 1fr;
      gap:10px;
      align-items:start;
      padding:9px;
      border:1px solid var(--line);
      border-radius:6px;
      background:var(--panel2);
    }}
    .rule strong {{ font-size:12px; color:var(--ink); }}
    .rule span {{ color:var(--muted); }}
    .note {{
      border:1px solid color-mix(in srgb, var(--lock) 45%, var(--line));
      border-left:4px solid var(--lock);
      border-radius:7px;
      padding:12px;
      background:#170f10;
      color:#ffd8d8;
    }}
    .caption {{ color:var(--muted); font-size:12px; margin-top:8px; }}
    @media (max-width:960px) {{
      .grid, .modules {{ grid-template-columns:1fr; }}
      .stats {{ grid-template-columns:1fr; }}
      .rule {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="kicker">OMIJA INPUT ROLE MAP</div>
    <h1>StealthMole은 입력단, Omija는 판단 엔진</h1>
    <div class="sub">이 화면은 민감 데이터 조회 화면이 아니다. 네 개 입력 모듈이 어떤 온톨로지 객체와 링크로 정규화되고, 어떤 판단 객체로 이어지는지 보여주는 발표용 역할 지도다.</div>
  </header>
  <main>
    <div class="legend">
      <span class="chip vendor">PRIVATE_FEED contract</span>
      <span class="chip seed">SEED synthetic object</span>
      <span class="chip public">PUBLIC_CONTEXT</span>
      <span class="chip engine">ENGINE reasoning</span>
      <span class="chip decision">DECISION object</span>
      <span class="chip locked">LOCKED sensitive surface</span>
    </div>

    <section class="panel">
      <h2>1. 입력 모듈은 증거 후보를 제공하고, 온톨로지가 의미를 만든다</h2>
      <div class="modules">{modules}</div>
    </section>

    <section class="network">
      <svg viewBox="0 0 1120 520" role="img" aria-label="StealthMole module to Omija ontology graph">
        <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#59616c"/></marker></defs>
        <path class="edge vendor" d="M180 95 C245 95 280 125 342 125"/>
        <path class="edge vendor" d="M180 175 C245 175 280 210 342 210"/>
        <path class="edge vendor" d="M180 255 C245 255 280 295 342 295"/>
        <path class="edge vendor" d="M180 335 C245 335 280 295 342 295"/>
        <path class="edge locked" d="M500 210 C560 210 585 210 640 210"/>
        <path class="edge engine" d="M500 125 C560 125 580 105 640 105"/>
        <path class="edge engine" d="M500 210 C560 210 585 155 640 155"/>
        <path class="edge engine" d="M500 295 C560 295 590 260 640 260"/>
        <path class="edge public" d="M500 395 C560 395 585 330 640 330"/>
        <path class="edge engine" d="M795 105 C845 105 865 130 920 130"/>
        <path class="edge engine" d="M795 155 C845 155 865 195 920 195"/>
        <path class="edge engine" d="M795 260 C845 260 865 260 920 260"/>
        <path class="edge decision" d="M795 330 C850 330 870 330 920 330"/>
        <path class="edge decision" d="M1010 130 C1040 160 1040 230 1010 260"/>
        <path class="edge decision" d="M1010 260 C1040 285 1040 310 1010 330"/>

        <g class="node vendor"><rect x="35" y="65" width="145" height="60"/><text x="54" y="93">CL</text><text x="54" y="111" class="small">leaked identities</text></g>
        <g class="node vendor"><rect x="35" y="145" width="145" height="60"/><text x="54" y="173">CDS</text><text x="54" y="191" class="small">infostealer device</text></g>
        <g class="node vendor"><rect x="35" y="225" width="145" height="60"/><text x="54" y="253">DT</text><text x="54" y="271" class="small">darkweb context</text></g>
        <g class="node vendor"><rect x="35" y="305" width="145" height="60"/><text x="54" y="333">TT</text><text x="54" y="351" class="small">telegram context</text></g>

        <g class="node seed"><rect x="342" y="90" width="158" height="70"/><text x="362" y="120">CredentialExposure</text><text x="362" y="140" class="small">of + targets split</text></g>
        <g class="node seed"><rect x="342" y="175" width="158" height="70"/><text x="362" y="205">InfectedDevice</text><text x="362" y="225" class="small">session / recency hints</text></g>
        <g class="node seed"><rect x="342" y="260" width="158" height="70"/><text x="362" y="290">ThreatSource</text><text x="362" y="310" class="small">provenance support</text></g>
        <g class="node public"><rect x="342" y="360" width="158" height="70"/><text x="362" y="390">Open context</text><text x="362" y="410" class="small">KEV/NVD/ATT&CK</text></g>

        <g class="node locked"><rect x="640" y="185" width="155" height="70"/><text x="660" y="215">Adapter boundary</text><text x="660" y="235" class="small">mask / normalize / dedup</text></g>
        <g class="node engine"><rect x="640" y="70" width="155" height="60"/><text x="660" y="98">Identity owner</text><text x="660" y="116" class="small">who owns the account</text></g>
        <g class="node engine"><rect x="640" y="140" width="155" height="60"/><text x="660" y="168">Target asset</text><text x="660" y="186" class="small">what it reaches</text></g>
        <g class="node engine"><rect x="640" y="250" width="155" height="60"/><text x="660" y="278">Supplier chain</text><text x="660" y="296" class="small">T2 -> T1 -> Prime</text></g>
        <g class="node engine"><rect x="640" y="320" width="155" height="60"/><text x="660" y="348">Active triage</text><text x="660" y="366" class="small">band before volume</text></g>

        <g class="node decision"><rect x="920" y="100" width="160" height="60"/><text x="940" y="128">RiskAssessment</text><text x="940" y="146" class="small">supplier priority</text></g>
        <g class="node decision"><rect x="920" y="165" width="160" height="60"/><text x="940" y="193">CompromiseIncident</text><text x="940" y="211" class="small">path snapshot</text></g>
        <g class="node decision"><rect x="920" y="230" width="160" height="60"/><text x="940" y="258">ProgramExposure</text><text x="940" y="276" class="small">blast radius</text></g>
        <g class="node decision"><rect x="920" y="295" width="160" height="60"/><text x="940" y="323">NotificationDraft</text><text x="940" y="341" class="small">human review</text></g>
      </svg>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>2. 현재 데모가 실제로 관리하는 구조</h2>
        <div class="stats">{seed_stats}</div>
        <div class="caption">개체 값은 synthetic이지만, Foundry 온톨로지에 올릴 수 있는 객체/링크 형태로 관리된다.</div>
      </div>
      <div class="panel">
        <h2>3. 공개 context는 배경 증거로만 쓴다</h2>
        <div class="stats">{public_stats}</div>
        <div class="caption">Generated at: {e(public["generated_at"])}. 공개 데이터는 자격증명 증거가 아니라 asset-risk 설명 재료다.</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>4. 판단 객체로 바뀌는 순간</h2>
        <div class="stats">{decision_stats}</div>
        <div class="caption">Omija의 산출물은 feed row가 아니라, 상태 전이와 근거 링크를 갖는 decision object다.</div>
      </div>
      <div class="panel">
        <h2>5. 발표자가 반드시 말할 경계</h2>
        <div class="rules">
          <div class="rule"><strong>감지 위치</strong><span>외부 입력 공급원은 신호를 제공한다. Omija는 그 신호를 방산 공급망 경로 위에서 판단한다.</span></div>
          <div class="rule"><strong>민감 표면</strong><span>실제 계정, 비밀번호, 쿠키, 세션 원문은 데모 페이지와 저장소에 올리지 않는다.</span></div>
          <div class="rule"><strong>차별점</strong><span>유출량 순위가 아니라 `of` / `targets` / `subcontractsTo` / `traverses_*` 경로가 우선순위를 만든다.</span></div>
          <div class="rule"><strong>조치 방식</strong><span>자동 발송이 아니라 `NotificationDraft`까지 만든 뒤 사람이 검토하고 export한다.</span></div>
        </div>
      </div>
    </section>

    <div class="note">
      이 페이지는 민감 데이터 탐색 결과가 아니다. 발표에서는 “이런 유형의 신호가 승인된 공급원에서 들어오면, 같은 온톨로지 파이프를 타고 이런 판단 객체가 생긴다”는 구조 증명으로만 사용한다.
    </div>
  </main>
</body>
</html>
"""


def main() -> int:
    payload = build_payload()
    OUT_HTML.write_text(render(payload), encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(REPO_ROOT)}")
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
