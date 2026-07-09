# RoXX Production Operations

## Production Bootstrap

Use the unified launcher to create runtime directories, a persistent session secret, TLS material, and a non-sensitive bootstrap summary:

```bash
sudo ROXX_CONFIG_DIR=/etc/roxx ROXX_DATA_DIR=/var/lib/roxx ROXX_LOG_DIR=/var/log/roxx \
  roxx setup --non-interactive --hostname roxx.example.com \
  --binary /usr/bin/roxx --working-directory /var/lib/roxx --install-service
```

Review `/etc/roxx/roxx.env`, replace generated TLS material with a certificate issued by the production CA when required, then restart the service. The production profile refuses to start without a persistent `ROXX_SECRET_KEY`, enables secure cookies and HSTS, and adds CSP, referrer and permissions-policy headers.

## Observability

- `/livez` reports process liveness.
- `/readyz` checks writable runtime directories, SQLite access, and optional named TCP dependencies from `ROXX_READINESS_TCP_TARGETS`.
- `/metrics` exports Prometheus text metrics. Set `ROXX_METRICS_TOKEN` to require a bearer token.
- `roxx audit export --output audit.jsonl` exports chronological JSON Lines records for SIEM ingestion or archival.
- Service logs rotate at 10 MiB with five backups in `ROXX_LOG_DIR/roxx-server.log`.

Readiness target values use `name=host:port` entries separated by commas. Probe responses expose only normalized names and booleans, never addresses, credentials, exceptions, or latency details.

## High Availability

RoXX supports two documented patterns:

1. Active/passive: deploy identical nodes, keep configuration and certificates synchronized through the operator's secret/configuration system, and move a virtual IP with Keepalived only when `/readyz` succeeds. Start from `deploy/ha/keepalived.conf.example` and use a different priority on each node.
2. Load balanced: deploy at least two nodes behind HAProxy using `deploy/ha/haproxy.cfg`. Health checks remove unready nodes. Sticky cookies preserve local web sessions; shared authentication databases and a stable `ROXX_SECRET_KEY` are required before removing stickiness.

Do not copy live SQLite files between active nodes. Use a supported shared SQL backend for shared state where available, or operate the web administration plane active/passive. RADIUS authentication backends should be configured identically on all nodes.

## Upgrade And Rollback

Back up configuration, data, certificates, and the currently installed binary before every upgrade. Validate SHA256 checksums and GitHub attestations before installation:

```bash
sha256sum --check SHA256SUMS.txt
gh attestation verify roxx-linux-x86_64 -R tsautier/RoXX
sudo sh scripts/upgrade_linux.sh ./roxx-linux-x86_64 /usr/bin/roxx
```

The Linux upgrade script stops the service, preserves the current binary under `/var/lib/roxx/rollback`, starts the candidate, polls `/readyz`, and restores the previous binary automatically on failure. Package installations can also be rolled back with the distribution package manager using the previous `.deb` or `.rpm` asset.

On Windows, run elevated PowerShell:

```powershell
.\scripts\upgrade_windows.ps1 -Source .\roxx.exe
```

The Windows script backs up the installed executable under `%ProgramData%\RoXX\rollback`, uses the existing Windows service, polls readiness, restores the previous executable on failure, and prints recent Application event-log entries.

## Release Signing And Provenance

The release workflow always generates SHA256 checksums, SPDX 2.3 SBOMs, signed GitHub/Sigstore provenance, and signed SBOM attestations. Configure both repository secrets below to additionally Authenticode-sign `roxx.exe`:

- `ROXX_WINDOWS_CERTIFICATE`: base64-encoded PFX certificate.
- `ROXX_WINDOWS_CERTIFICATE_PASSWORD`: PFX password.

Without those secrets the workflow publishes an explicitly unsigned Windows executable; provenance and checksums still apply. Verify Authenticode locally with `Get-AuthenticodeSignature .\roxx.exe`.

## Platform Compatibility

The scheduled `Platform Compatibility` workflow runs the complete suite on Ubuntu 22.04, Ubuntu 24.04, Windows Server 2022 and Windows Server 2025. This CI matrix verifies application behavior on GitHub-hosted images; it does not certify every kernel, domain policy, HSM, network appliance, or third-party identity provider configuration.
