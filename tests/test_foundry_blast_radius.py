import pytest

from scripts.foundry_blast_radius import summarize_blast_radius


class FakeStore:
    def all_exposures(self):
        return [
            {
                "id": "exp:micro-h:active",
                "identity_ref": "id:ops@micro-h.example",
                "domain_ref": "micro-h.example",
                "target_domain_ref": "vpn.prime-x.example",
                "source_ref": "src:seed",
                "has_session_cookie": True,
                "supplier_id": "sup-h",
            }
        ]

    def propagation_paths(self, supplier_id, *, depth_cap=6):
        assert supplier_id == "sup-h"
        return [
            [
                {"type": "Supplier", "ref": "sup-h"},
                {"type": "Supplier", "ref": "sup-f"},
                {"type": "Prime", "ref": "prime-x"},
                {"type": "Program", "ref": "prog-sentinel"},
            ],
            [
                {"type": "Supplier", "ref": "sup-h"},
                {"type": "Supplier", "ref": "sup-f"},
                {"type": "Prime", "ref": "prime-x"},
                {"type": "Program", "ref": "prog-harbor"},
            ],
        ]

    def incidents_for_supplier(self, supplier_id):
        assert supplier_id == "sup-h"
        return [
            {
                "id": "incident:micro-h:active",
                "risk_band": "A",
                "path_confidence": 0.9,
                "path_hash": "pathhash:micro-h-active",
                "path_snapshot": '["exp:micro-h:active","sup-h","prog-sentinel"]',
                "path": ["exp:micro-h:active", "sup-h", "prog-sentinel"],
            }
        ]


def test_summarize_blast_radius_links_exposure_to_programs():
    summary = summarize_blast_radius(FakeStore(), "exp:micro-h:active")

    assert summary["supplier"] == "sup-h"
    assert summary["programs"] == ["prog-harbor", "prog-sentinel"]
    assert summary["provenance"]["incident"] == "incident:micro-h:active"
    assert summary["exposure"]["target_domain"] == "vpn.prime-x.example"


def test_summarize_blast_radius_fails_for_unknown_exposure():
    with pytest.raises(SystemExit, match="exposure not found"):
        summarize_blast_radius(FakeStore(), "exp:missing")
