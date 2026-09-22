# Installation Lifecycle Pilot

The [Installation pilot workflow](https://github.com/tsautier/RoXX/actions/workflows/install-pilot.yml) tests published assets on disposable GitHub-hosted runners. Supply a published tag when dispatching it. The pull-request run builds the candidate Windows executable and uses the latest published Debian package with the changed lifecycle scripts.

## Windows runner

- Installs the single `roxx.exe` from the release archive into a temporary directory and registers `RoXXWebServer`.
- Confirms that the service command line points to that executable, then starts, probes `/readyz`, stops, and restarts it.
- Runs a healthy upgrade, then an intentionally invalid upgrade and confirms that the previous executable hash and readiness return.
- Reads `roxx-server.log` and recent Application events, removes the service and executable, and checks that neither remains installed.

## Ubuntu runner

- Installs the published Debian package natively with `dpkg`, starts the systemd unit, probes `/readyz`, stops, and restarts it.
- Upgrades from the published standalone executable, then injects a failing replacement and checks the restored binary hash and readiness.
- Reads the service journal and rotating log, removes the package, and confirms that `/usr/bin/roxx` is gone.

## Evidence and limits

The pre-release candidate passed the [Windows and Debian pilot](https://github.com/tsautier/RoXX/actions/runs/35781050632) and [Python CI](https://github.com/tsautier/RoXX/actions/runs/35781050731). These runs validate disposable GitHub-hosted machines, not a domain-joined Windows Server, a RHEL-compatible package installation, or production HA. The workflow probes the administration server, not RADIUS authentication: RoXX does not itself listen on UDP 1812. A RADIUS access test needs the documented FreeRADIUS module, a test identity provider, and a RADIUS client.
