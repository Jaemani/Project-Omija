"""P4 dashboard tests.

Covers:
  (d) the rendered dashboard HTML leaks NO raw secret, AND active-compromise
      suppliers are pinned to the TOP of the ranking table,
  plus the presence of the propagation graph, drilldown panels (with the P5
  draft preview), and the tier/active/grade filters.
"""

import re

from actions.notify_draft import generate_drafts
from actions.propagate_risk import propagate_program_risk
from adapter.mock import DEMO_NOW, MockExposureSource
from scripts.p4_dashboard import build_dashboard_html, run
from scripts.p5_drafts import build_pipeline


def _dashboard():
    store, assessments = build_pipeline(DEMO_NOW)
    generate_drafts(store, assessments, top=3, now=DEMO_NOW)   # P4↔P5 link
    propagate_program_risk(store, now=DEMO_NOW)                # P4 program roll-up
    html = build_dashboard_html(store, assessments, DEMO_NOW)
    return store, assessments, html


def test_dashboard_has_no_raw_secret():
    """(d.1) Masking guardrail on the rendered page."""
    store, _a, html = _dashboard()
    leaked = [s for s in MockExposureSource().raw_secrets() if s in html]
    assert leaked == [], f"raw secret rendered in dashboard: {leaked}"
    assert not re.findall(r"Synthetic-[A-Za-z]+-\d+!", html)
    assert not re.findall(r"SID[0-9a-f]{20,}", html)
    assert "***" in html          # masked markers are rendered
    store.close()


def test_dashboard_active_rows_pinned_on_top():
    """(d.2) Every active row precedes every non-active row in the ranking table."""
    store, _a, html = _dashboard()
    body = html.split('id="rank-body">', 1)[1].split("</tbody>", 1)[0]
    flags = [int(m) for m in re.findall(r'data-active="(\d)"', body)]
    assert flags, "no ranking rows found"
    assert flags[0] == 1                          # at least one active, first
    assert flags == sorted(flags, reverse=True)   # all 1s before any 0
    store.close()


def test_dashboard_has_graph_drilldown_and_filters():
    store, _a, html = _dashboard()
    # inline SVG propagation graph with the full active chain + shared prime/program
    assert "<svg" in html and 'class="graph"' in html
    assert "InfectedDevice" in html and "Program" in html
    assert "Xenon Aerospace" in html            # prime node (fits)
    assert "Sentinel ISR" in html               # program node label (title tooltip / node)
    # the active incident chain surfaces the full program name in the drilldown
    assert "Harbor Sustainment Program" in html
    # drilldown panels + the P5 draft preview (P4↔P5 connection)
    assert 'id="drill-sup-a"' in html
    assert "통보 초안 미리보기" in html
    # filters: tier / active-only / grade
    assert 'id="f-tier"' in html
    assert 'id="f-active"' in html
    assert 'id="f-grade"' in html
    # self-contained: no external resource references
    assert not re.search(r'(src|href)\s*=\s*"https?://', html)
    store.close()


def test_dashboard_has_program_exposure_rollup():
    """The program roll-up section renders, marks programs BURNING, and surfaces
    a multi-tier active chain (2차 terminal → tier-1 → Prime → Program)."""
    store, _a, html = _dashboard()
    assert "프로그램 노출" in html                       # program roll-up section
    assert "BURNING" in html                             # a burning program
    assert "programs burning" in html                    # KPI
    # the multi-tier money-shot chain surfaces on the page
    assert "Hotel Microelectronics" in html and "Foxtrot Metals" in html
    store.close()


def test_p4_dashboard_runs_green():
    """P4 CLI smoke: full pipe + render returns RESULT: OK."""
    assert run() == 0
