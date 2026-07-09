# RoXX v1.0.2 Release Notes

**Release Date:** July 10, 2026
**Tag:** v1.0.2

RoXX v1.0.2 extends the single-application-command model to pip installations on Linux. The package now installs only the `roxx` command, matching the single `roxx.exe` application published for Windows.

## Highlights

- One installed application command on every platform: `roxx` on Linux and `roxx.exe` on Windows.
- Server mode now starts with `roxx server`.
- Linux service generation now uses `roxx service print-systemd` and writes `ExecStart=.../roxx server`.
- Setup and service management remain available as `roxx setup`, `roxx service ...`, and `roxx windows-service ...`.

## Required Linux Upgrade

This release removes the legacy `roxx-server`, `roxx-service`, `roxx-console`, `roxx-setup`, `roxx-web`, and `roxx-windows-service` pip entry points. Existing systemd units that refer to `roxx-server` must be regenerated or edited before restarting RoXX.

To regenerate the unit for a virtual-environment installation:

```bash
sudo -u roxx /opt/roxx/app/venv/bin/roxx service print-systemd \
  --binary /opt/roxx/app/venv/bin/roxx \
  --user roxx \
  --group roxx \
  --working-directory /opt/roxx/app \
  --config-dir /etc/roxx \
  --data-dir /var/lib/roxx \
  --log-dir /var/log/roxx | sudo tee /etc/systemd/system/roxx.service
sudo systemctl daemon-reload
sudo systemctl restart roxx
sudo systemctl status roxx
```

The resulting unit must contain:

```ini
ExecStart=/opt/roxx/app/venv/bin/roxx server
```

## Verification

- Full Python test suite: `124 passed`.
- Syntax-critical Ruff checks: passed.
- Source distribution and wheel build: passed.
- Wheel metadata contains only the `roxx = roxx.__main__:main` console entry point.
- Local PyInstaller build contains only `roxx.exe`.
- Executable smoke checks: systemd rendering, `/livez`, and `/readyz` passed.

## Release Assets

- `roxx.exe`
- `roxx-windows-v1.0.2.zip`
- `SHA256SUMS.txt`

Windows release assets remain unchanged in structure: the release contains one raw application executable and one ZIP archive containing that executable.
