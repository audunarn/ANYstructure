from __future__ import annotations

from pathlib import Path

import anystruct


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_license_metadata_agree() -> None:
    setup = (ROOT / "setup.py").read_text(encoding="utf-8")
    root_package = (ROOT / "__init__.py").read_text(encoding="utf-8")

    assert "version='6.4.0'" in setup
    assert "license='MPL-2.0'" in setup
    assert "license_files=['LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'docs/LICENSE.md']" in setup
    assert "Mozilla Public License 2.0 (MPL 2.0)" in setup
    assert "__version__ = '6.4.0'" in root_package
    assert "__license__ = 'MPL-2.0'" in root_package
    assert anystruct.__version__ == "6.4.0"
    assert anystruct.__license__ == "MPL-2.0"
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith(
        "Mozilla Public License Version 2.0\n"
    )


def test_readme_places_core_workflow_before_fem_integration() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.index("## Core structural design") < readme.index(
        "## Finite-element integration"
    )


def test_release_notices_are_in_source_distribution_manifest() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    for name in (
        "LICENSE",
        "NOTICE",
        "THIRD_PARTY_NOTICES.md",
        "TRADEMARKS.md",
        "docs/LICENSE.md",
    ):
        assert f"include {name}" in manifest
