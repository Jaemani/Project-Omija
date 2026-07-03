"""(g) P1 report generation: content present, active rows highlighted, and NO
raw secret survives into the rendered HTML (masking guardrail)."""

import re

from adapter.mock import MockExposureSource
from scripts.p1_report import DEMO_NOW, build_report_html, build_store


def test_report_contains_supplier_names_and_provenance():
    store, result, written = build_store()
    html = build_report_html(store, result, DEMO_NOW)
    assert written > 0 and result.matched_exposures > 0
    # a hit supplier name appears
    assert "Alpha Precision" in html
    # provenance handle (source_ref) is cited somewhere
    assert "cds-supplier-a.example-active" in html
    store.close()


def test_report_highlights_active_signal():
    store, result, _ = build_store()
    html = build_report_html(store, result, DEMO_NOW)
    assert "ACTIVE" in html
    assert "active-row" in html  # the highlighted row class is emitted
    store.close()


def test_report_shows_propagation_path():
    store, result, _ = build_store()
    html = build_report_html(store, result, DEMO_NOW)
    # Supplier → Prime → Program surfaced
    assert "Xenon Aerospace" in html
    assert "Sentinel ISR Program" in html
    store.close()


def test_report_has_no_raw_secret():
    """CLAUDE.md guardrail: raw secrets must never appear on screen."""
    store, result, _ = build_store()
    html = build_report_html(store, result, DEMO_NOW)

    src = MockExposureSource()
    leaked = [s for s in src.raw_secrets() if s in html]
    assert leaked == [], f"raw secret rendered in report: {leaked}"

    # defensive pattern sweep for the synthetic secret shapes
    assert not re.findall(r"Synthetic-[A-Za-z]+-\d+!", html)
    assert not re.findall(r"SID[0-9a-f]{20,}", html)
    store.close()


def test_report_masked_values_present():
    store, result, _ = build_store()
    html = build_report_html(store, result, DEMO_NOW)
    assert "***" in html  # masked secret markers rendered
    store.close()
