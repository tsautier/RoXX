# RoXX v1.1.2 Release Notes

**Release Date:** September 22, 2026
**Tag:** v1.1.2

## Service lifecycle

- Fixed the single Windows executable's Service Control Manager entry point. Services installed with earlier releases can be stopped and removed, then reinstalled with this version; replacing the executable alone does not update the registered service command line.
- Windows upgrades and removal now wait for PyInstaller to release the executable after the service reports that it has stopped.
- Linux upgrades restore the previous executable when the replacement service fails to start immediately.
- Added a manual installation pilot workflow for published release assets. The pre-release validation ran Windows service registration, start, stop, restart, upgrade, failed-upgrade rollback, logs, and removal on a disposable GitHub-hosted Windows runner. Debian package installation and the equivalent Linux lifecycle passed on a disposable Ubuntu runner.
- Clarified the deployment architecture in the README and website: RoXX relies on the documented FreeRADIUS integration for inbound RADIUS requests rather than opening UDP 1812 in `roxx server`.

## Upgrade from 1.1.1

On Windows, stop and remove the existing `RoXXWebServer` service using the previous `roxx.exe`, then install the v1.1.2 executable with `scripts/install_windows.ps1`. Back up configuration and data first. The registration must be recreated because the service command line now includes `windows-service run`. Use the normal readiness probe after restarting. Linux packages retain the same systemd unit and do not require a unit migration.

## Verification limits

The installation pilot uses GitHub-hosted disposable machines, not a domain-joined Windows Server or a representative enterprise Linux host. The Debian package is exercised natively; RPM installation/removal still needs a disposable RHEL-compatible host. A real RADIUS client authentication check requires a configured FreeRADIUS integration and test identity provider. No production HA or external-provider behavior is certified by this release.
