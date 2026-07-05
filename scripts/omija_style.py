"""Shared visual system for the Omija demo surfaces (omija_demo, omija_console_home).

Single source of truth for:
  * the dark Palantir-esque design tokens (lifted from scripts/palantir_pages.py,
    dataviz categorical palette validated on #1a1a19),
  * the PROVENANCE CHIP system — the four-level real/synthetic separation that
    enforces the claim architecture "데이터는 가상, 시스템은 진짜":
        LIVE·Foundry  — read back from the actual Foundry ontology/actions
        ENGINE·실측    — computed by the real local engine at generation time
        SEED·가상      — synthetic entity data (fictional orgs/credentials)
        FRAME·연출     — scenario-framing numbers (labeled, never implied real)
  * the SYNTHETIC banner + the chip legend pinned under it,
  * the collapsible 발표 노트 (presenter note) block.

No network, no CDN — everything inlined by the page generators.
"""

from __future__ import annotations

import html


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


# --------------------------------------------------------------------------- #
# provenance chips
# --------------------------------------------------------------------------- #
CHIP_LEVELS: dict[str, tuple[str, str]] = {
    "live":  ("live",  "LIVE·Foundry"),
    "eng":   ("eng",   "ENGINE·실측"),
    "seed":  ("seed",  "SEED·가상"),
    "frame": ("frame", "FRAME·연출"),
}


def chip(level: str) -> str:
    cls, label = CHIP_LEVELS[level]
    return f'<span class="pchip {cls}">{esc(label)}</span>'


CHIP_LEGEND_SENTENCES: dict[str, str] = {
    "live":  "오늘 실제 Foundry 온톨로지·액션에서 읽어온 플랫폼 상태.",
    "eng":   "페이지 생성 시점에 로컬 엔진이 실제로 계산한 값 — 입력만 합성이다.",
    "seed":  "합성 시드의 가상 개체 — 조직·계정·도메인 전부 *.example.",
    "frame": "운영 규모·맥락을 위한 연출 수치 — 이 칩이 붙은 것만 연출이다.",
}

CLAIM_LINE = (
    "이 도메인은 실제 유출 자격증명으로 시연할 수 없다 — 그래서 "
    "<b>개체는 가상이고, 개체를 다루는 시스템 전부가 진짜다.</b>"
)


def synthetic_banner() -> str:
    return """
<div class="synbar">
  <span class="dot"></span>
  <b>SYNTHETIC DEMO SCENARIO</b>
  <span class="kr">가상 시나리오 — 실제 조직·자격증명 아님 · 모든 도메인은 합성 *.example · 비밀값 전량 마스킹(•••)</span>
</div>"""


def chip_legend() -> str:
    rows = "".join(
        f'<div class="pl-item">{chip(level)}<span>{esc(sentence)}</span></div>'
        for level, sentence in CHIP_LEGEND_SENTENCES.items()
    )
    return f"""
<div class="provlegend"><div class="wrap">
  <div class="pl-row">{rows}</div>
  <div class="pl-claim">{CLAIM_LINE}</div>
</div></div>"""


# --------------------------------------------------------------------------- #
# product nav — one thin strip shared by the four surfaces so they read as a
# single product, not four loose files.
# --------------------------------------------------------------------------- #
NAV_ITEMS: list[tuple[str, str]] = [
    ("omija_console_home.html", "평시 콘솔"),
    ("omija_demo.html",         "사건 보고서"),
    ("data_coverage_map.html",  "커버리지 맵"),
    ("data_evidence_brief.html", "데이터 증거"),
    ("program_threat_view.html", "프로그램 뷰"),
]

# Self-contained: carries its own <style> with hardcoded dark tokens so it looks
# identical whether or not the host page also loaded TOKENS_CSS (the coverage
# map and program view pages do not). No animation / external refs — clears the
# per-page safety checks. Duplicated inline per page is fine (separate files).
NAV_CSS = """
.omija-nav{background:#111110;border-bottom:1px solid #262624;
  font-family:ui-monospace,SFMono-Regular,Menlo,"Cascadia Code",monospace}
.omija-nav .onav-wrap{max-width:1180px;margin:0 auto;padding:0 20px;
  display:flex;align-items:center;gap:14px;min-height:34px;flex-wrap:wrap}
.omija-nav .onav-brand{font-size:10px;letter-spacing:2px;color:#6f6e68;font-weight:600;flex:none}
.omija-nav .onav-items{display:flex;align-items:stretch;flex-wrap:wrap}
.omija-nav a.onav-item{font-size:11px;letter-spacing:.4px;color:#a9a89f;text-decoration:none;
  padding:8px 12px;border-bottom:2px solid transparent;white-space:nowrap}
.omija-nav a.onav-item:hover{color:#ececea;background:rgba(255,255,255,.03)}
.omija-nav a.onav-item.cur{color:#ececea;border-bottom-color:#3987e5}
.omija-nav a.onav-item.cur::before{content:"● ";color:#3987e5;font-size:8px}
/* narrow: brand takes its own line so all four items get a clean full-width row;
   items still wrap (never clip) and horizontally scroll as a last resort */
@media(max-width:480px){
  .omija-nav .onav-wrap{gap:4px 14px;padding:0 14px}
  .omija-nav .onav-brand{width:100%}
  .omija-nav .onav-items{flex-wrap:wrap;overflow-x:auto;max-width:100%}
}
"""


def nav_strip(current_page: str) -> str:
    """Thin product-wide nav shared across the four Omija surfaces.

    `current_page` is the basename of the active .html file; that item is marked
    (blue underline + dot + aria-current) and the others link to it with relative
    hrefs (all pages ship to the same output dir). Sits directly under the
    SYNTHETIC banner on the two console pages; at the very top on the standalone
    coverage/program pages."""
    links = []
    for href, label in NAV_ITEMS:
        cur = href == current_page
        cls = "onav-item cur" if cur else "onav-item"
        aria = ' aria-current="page"' if cur else ""
        links.append(f'<a class="{cls}" href="{esc(href)}"{aria}>{esc(label)}</a>')
    return f"""<style>{NAV_CSS}</style>
<nav class="omija-nav" aria-label="Omija surfaces">
  <div class="onav-wrap">
    <span class="onav-brand">OMIJA</span>
    <div class="onav-items">{''.join(links)}</div>
  </div>
</nav>"""


def pnote(section_no: str, sentences: list[str]) -> str:
    """Collapsible presenter note (발표 노트) — what to SAY at this scroll
    position, including which chips to point at."""
    body = " ".join(sentences)
    return f"""
<details class="pnote"><summary>발표 노트 · {esc(section_no)}</summary>
  <div class="pb">{body}</div>
</details>"""


# --------------------------------------------------------------------------- #
# shared CSS
# --------------------------------------------------------------------------- #
TOKENS_CSS = """
:root{
  --plane:#0d0d0d; --surface:#141413; --surface-2:#1a1a19; --raised:#201f1d;
  --ink:#ececea; --ink-2:#a9a89f; --muted:#6f6e68;
  --hair:#262624; --hair-2:#35342f;
  /* validated dark-mode CATEGORICAL hues (dataviz reference, dark column) */
  --c-entity:#3987e5;    /* blue   — entity / registry structure */
  --c-evidence:#199e70;  /* aqua   — observed evidence */
  --c-derived:#c98500;   /* yellow — derived judgment */
  --c-output:#9085e9;    /* violet — human / output */
  --cross:#ec835a;       /* reserved status 'serious' — the single targets cross-edge */
  /* triage bands = fixed status ramp (never a series colour) */
  --band-a:#d03b3b;      /* critical — active compromise path */
  --band-b:#fab219;      /* warning  — elevated exposure */
  --band-c:#3987e5;      /* recessive— observed / passive */
  --good:#2fa46a;
  --mono:ui-monospace,SFMono-Regular,Menlo,"Cascadia Code",monospace;
  --sans:system-ui,-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--plane);color:var(--ink);
  font-family:var(--sans);font-size:14px;line-height:1.55;-webkit-font-smoothing:antialiased}
body{overflow-x:hidden}
a{color:var(--c-entity)}
h1,h2,h3{margin:0;font-weight:600;letter-spacing:.2px}
code,kbd,.mono{font-family:var(--mono)}
.scroll-x{overflow-x:auto;overflow-y:hidden}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}

/* SYNTHETIC banner — unmissable, not ugly */
.synbar{display:flex;align-items:center;gap:12px;padding:9px 20px;
  background:linear-gradient(90deg,rgba(250,178,25,.14),rgba(250,178,25,.04));
  border-bottom:1px solid rgba(250,178,25,.4);position:sticky;top:0;z-index:20;
  font-size:12.5px;color:#f4d58a}
.synbar .dot{width:8px;height:8px;border-radius:50%;background:var(--band-b);
  box-shadow:0 0 8px var(--band-b);flex:none}
.synbar b{color:#ffe6a6;font-family:var(--mono);letter-spacing:.5px}
.synbar .kr{color:#d9c184}

/* provenance chips — the real/synthetic separation, fixed colors */
.pchip{display:inline-flex;align-items:center;gap:5px;font-family:var(--mono);
  font-size:9px;letter-spacing:.6px;padding:1px 7px;border-radius:3px;
  border:1px solid;vertical-align:middle;white-space:nowrap;font-weight:500}
.pchip::before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor;flex:none}
.pchip.live {color:#4fc596;border-color:rgba(25,158,112,.5); background:rgba(25,158,112,.08)}
.pchip.eng  {color:#6ea6ec;border-color:rgba(57,135,229,.5); background:rgba(57,135,229,.08)}
.pchip.seed {color:#9d9c93;border-color:rgba(111,110,104,.6);background:rgba(111,110,104,.10)}
.pchip.frame{color:#f0b73f;border-color:rgba(250,178,25,.5); background:rgba(250,178,25,.08)}

/* chip legend — pinned directly under the banner */
.provlegend{border-bottom:1px solid var(--hair);background:var(--surface-2);padding:9px 0}
.pl-row{display:flex;flex-wrap:wrap;gap:7px 22px}
.pl-item{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--ink-2)}
.pl-claim{margin-top:7px;font-size:12px;color:var(--ink-2)}
.pl-claim b{color:var(--ink)}
/* narrow: each legend item takes a full row; description wraps within padding */
@media(max-width:640px){
  .pl-row{gap:9px 0}
  .pl-item{width:100%;align-items:flex-start}
  .pl-item>span:not(.pchip){flex:1;min-width:0;overflow-wrap:anywhere}
}

/* masthead — flex row: title group grows, ver chip wraps below title on narrow */
.mast{border-bottom:1px solid var(--hair);background:var(--surface);padding:14px 0}
.mast .masthead{display:flex;align-items:flex-start;gap:8px 16px;flex-wrap:wrap}
.mast .mhead-main{flex:1 1 300px;min-width:0}
.mast .brand{font-family:var(--mono);font-size:12px;letter-spacing:1.6px;
  text-transform:uppercase;color:var(--ink)}
.mast .tag{font-size:12.5px;color:var(--ink-2);margin-top:3px}
.mast .ver{flex:0 0 auto;max-width:100%;font-family:var(--mono);font-size:10.5px;color:var(--muted);
  border:1px solid var(--hair-2);border-radius:3px;padding:2px 7px;white-space:nowrap}

section{padding:30px 0;border-bottom:1px solid var(--hair)}
.sec-k{font-family:var(--mono);font-size:10px;letter-spacing:1.6px;color:var(--muted);
  text-transform:uppercase;margin-bottom:9px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sec-h{font-size:19px;margin-bottom:5px}
.sec-sub{font-size:13px;color:var(--ink-2);margin-bottom:18px;max-width:860px}

/* presenter note (발표 노트) — unobtrusive collapsible */
details.pnote{margin-top:16px;border:1px dashed var(--hair-2);border-radius:6px;
  background:rgba(144,133,233,.04)}
details.pnote>summary{cursor:pointer;padding:7px 12px;font-family:var(--mono);
  font-size:10px;letter-spacing:1.2px;color:var(--c-output);text-transform:uppercase;
  list-style:none}
details.pnote>summary::-webkit-details-marker{display:none}
details.pnote>summary::before{content:"▸ "}
details.pnote[open]>summary::before{content:"▾ "}
details.pnote .pb{padding:2px 14px 12px;font-size:12.5px;color:var(--ink-2);line-height:1.75}
details.pnote .pb b{color:var(--ink)}

.footer{padding:18px 0 40px;color:var(--muted);font-size:11px;font-family:var(--mono)}

/* ---- responsive: keep the desktop-first layout from breaking on narrow ---- */
/* Body never scrolls horizontally (above); every wide element must wrap or live
   in a .scroll-x container so nothing important is hidden by that clip. */
@media(max-width:720px){
  section{padding:22px 0}
  .sec-h{font-size:17px}
  .sec-k{font-size:9.5px;letter-spacing:1.3px}
  .sec-sub{font-size:12.5px}
  .mast{padding:12px 0}
  /* SYNTHETIC banner: let the long KR line drop to its own full-width row */
  .synbar{flex-wrap:wrap;font-size:12px;padding:8px 16px;gap:8px 10px}
  .synbar .kr{flex:1 1 100%}
  .provlegend{padding:10px 0}
}
@media(max-width:480px){
  html,body{font-size:13.5px}
  section{padding:18px 0}
  .sec-h{font-size:15.5px}
  .synbar{font-size:11.5px}
}
"""
