"""Early-warning readiness gates collection plan plus ranking proof."""

from scripts.early_warning_readiness import build_readiness


def test_early_warning_readiness_passes_current_mvp_gates():
    readiness = build_readiness()

    assert readiness["ready"] is True
    assert readiness["summary"]["checks_passed"] == readiness["summary"]["checks_total"]
    assert readiness["summary"]["query_items"] == 118
    assert readiness["summary"]["asset_surface_seeds"] == 81
    assert readiness["summary"]["active_suppliers"] == ["sup-a", "sup-g", "sup-h"]


def test_early_warning_readiness_documents_limitations():
    readiness = build_readiness()
    limitations = " ".join(readiness["limitations"]).lower()

    assert "synthetic" in limitations
    assert "private feed query seeds are not executed" in limitations
    assert "confirmation" in limitations
