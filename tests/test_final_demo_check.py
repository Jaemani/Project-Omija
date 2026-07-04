from pathlib import Path

import scripts.final_demo_check as final_demo_check


def test_default_steps_are_fast_foundry_path_only():
    steps = final_demo_check.build_steps(supplier="sup-h", full=False)

    assert [step.name for step in steps] == [
        "Foundry OSDK link smoke",
        "SQLite vs Foundry decision compare",
        "Foundry blast radius",
        "Foundry HTML report",
    ]
    assert steps[1].argv[-2:] == ("--supplier", "sup-h")


def test_full_steps_include_local_regression_first():
    steps = final_demo_check.build_steps(supplier="sup-h", full=True)

    assert [step.name for step in steps[:3]] == [
        "Full test suite",
        "Local evaluation",
        "Local dashboard build",
    ]
    assert [step.name for step in steps[-4:]] == [
        "Foundry OSDK link smoke",
        "SQLite vs Foundry decision compare",
        "Foundry blast radius",
        "Foundry HTML report",
    ]


def test_verify_outputs_checks_required_files_and_html_markers(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    html_path = out_dir / "foundry_demo.html"
    compare_path = out_dir / "demo_e2e_compare.json"
    foundry_path = out_dir / "demo_e2e_foundry.json"
    sqlite_path = out_dir / "demo_e2e_sqlite.json"
    blast_path = out_dir / "blast_radius_exp_micro-h_active.json"

    html_path.write_text(
        "\n".join(
            [
                "Project Omija",
                "Risk band",
                "Impacted programs",
                "Active Path",
                "Provenance",
                "Raw record view",
            ]
        ),
        encoding="utf-8",
    )
    for path in (compare_path, foundry_path, sqlite_path, blast_path):
        path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(final_demo_check, "FOUNDRY_HTML", html_path)
    monkeypatch.setattr(
        final_demo_check,
        "REQUIRED_OUTPUTS",
        (compare_path, foundry_path, sqlite_path, blast_path, html_path),
    )
    monkeypatch.setattr(final_demo_check, "REPO_ROOT", Path(tmp_path))

    final_demo_check.verify_outputs()
