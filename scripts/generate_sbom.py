"""Generate a compact SPDX 2.3 SBOM for a RoXX release artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parent.parent


def _identifier(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.-]", "-", value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_sbom(artifact: Path) -> dict:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    artifact_hash = _sha256(artifact)
    root_id = "SPDXRef-Package-roxx"
    packages = [
        {
            "SPDXID": root_id,
            "name": "roxx",
            "versionInfo": project["version"],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "AGPL-3.0-or-later",
            "licenseDeclared": "AGPL-3.0-or-later",
            "checksums": [{"algorithm": "SHA256", "checksumValue": artifact_hash}],
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": f"pkg:pypi/roxx@{project['version']}",
                }
            ],
        }
    ]
    relationships = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": root_id,
        }
    ]

    for dependency_text in project["dependencies"]:
        requirement = Requirement(dependency_text)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            version = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError:
            version = "NOASSERTION"
        dependency_id = f"SPDXRef-Package-{_identifier(requirement.name)}"
        packages.append(
            {
                "SPDXID": dependency_id,
                "name": requirement.name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{requirement.name}@{version}",
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": root_id,
                "relationshipType": "DEPENDS_ON",
                "relatedSpdxElement": dependency_id,
            }
        )

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"roxx-{project['version']}-{artifact.name}",
        "documentNamespace": (
            f"https://github.com/tsautier/RoXX/sbom/{project['version']}/{artifact_hash}"
        ),
        "creationInfo": {
            "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "creators": ["Tool: RoXX scripts/generate_sbom.py"],
        },
        "packages": packages,
        "relationships": relationships,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(generate_sbom(args.artifact), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
