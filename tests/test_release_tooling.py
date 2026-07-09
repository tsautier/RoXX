"""Release metadata and artifact-generation tests."""

from __future__ import annotations

from scripts.generate_sbom import generate_sbom


def test_generate_sbom_describes_artifact(tmp_path):
    artifact = tmp_path / "roxx"
    artifact.write_bytes(b"binary")

    sbom = generate_sbom(artifact)

    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["packages"][0]["name"] == "roxx"
    assert sbom["packages"][0]["checksums"][0]["algorithm"] == "SHA256"
    assert any(item["relationshipType"] == "DEPENDS_ON" for item in sbom["relationships"])
