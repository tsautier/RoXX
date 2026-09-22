"""Release metadata and artifact-generation tests."""

from __future__ import annotations

from pathlib import Path

from scripts.generate_sbom import generate_sbom


def test_generate_sbom_describes_artifact(tmp_path):
    artifact = tmp_path / "roxx"
    artifact.write_bytes(b"binary")

    sbom = generate_sbom(artifact)

    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["packages"][0]["name"] == "roxx"
    assert sbom["packages"][0]["checksums"][0]["algorithm"] == "SHA256"
    assert any(item["relationshipType"] == "DEPENDS_ON" for item in sbom["relationships"])


def test_release_workflow_covers_all_supported_platforms_and_verifies_downloads():
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "windows-build:" in workflow
    assert "linux-build:" in workflow
    assert "macos-build:" in workflow
    assert "gh release download" in workflow
    assert "sha256sum --check SHA256SUMS.txt" in workflow
