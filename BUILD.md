# Build And Packaging Guide

## Python Package

```bash
python -m pip install build
python -m build
```

The wheel exposes one command: `roxx`.

## Standalone Application

Install build dependencies and build the application for the current operating system:

```bash
python -m pip install .[build]
python scripts/build_binaries.py
```

Windows produces only `dist/bin/roxx.exe`. Linux produces only `dist/bin/roxx`.

## Linux Packages

nFPM `v2.47.0` is used by CI to wrap the standalone Linux application, systemd unit and lifecycle scripts:

```bash
go install github.com/goreleaser/nfpm/v2/cmd/nfpm@v2.47.0
export PATH="$(go env GOPATH)/bin:$PATH"
export ROXX_VERSION="$(python -c 'import roxx; print(roxx.__version__)')"
sh scripts/build_linux_packages.sh
```

Outputs are written under `dist/packages/` as `.deb` and `.rpm` files.

## Windows Package

The tagged release workflow creates a ZIP containing one executable plus PowerShell scripts for installation, removal and guarded upgrade:

- `roxx.exe`
- `install_windows.ps1`
- `uninstall_windows.ps1`
- `upgrade_windows.ps1`

No secondary application executable is generated.

## Supply Chain

Every tagged release generates SHA256 checksums and SPDX 2.3 SBOMs. GitHub Actions signs provenance and SBOM attestations with `actions/attest@v4`. Authenticode signing runs only when `ROXX_WINDOWS_CERTIFICATE` and `ROXX_WINDOWS_CERTIFICATE_PASSWORD` repository secrets are configured.

## Verification

```bash
python -m ruff check . --select=E9,F63,F7,F82
python -m pytest
python -m build
python -m pip check
```

Also smoke-test the standalone application with `--help`, `service print-systemd`, `server`, `/livez`, `/readyz`, and its generated log file before publishing.
