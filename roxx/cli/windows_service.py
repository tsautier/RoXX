"""Windows service wrapper for the RoXX web server."""

from __future__ import annotations

import sys
import threading

try:  # pragma: no cover - exercised only on Windows with pywin32 installed
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:  # pragma: no cover - non-Windows fallback
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = None

from roxx.server.runtime import run_web_server


if win32serviceutil is not None:  # pragma: no branch
    class RoXXWindowsService(win32serviceutil.ServiceFramework):
        _svc_name_ = "RoXXWebServer"
        _svc_display_name_ = "RoXX Web Server"
        _svc_description_ = "Runs the RoXX HTTPS admin server as a Windows service."

        def __init__(self, args):
            super().__init__(args)
            self.h_wait_stop = win32event.CreateEvent(None, 0, 0, None)
            self.stop_event = threading.Event()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.stop_event.set()
            win32event.SetEvent(self.h_wait_stop)

        def SvcDoRun(self):
            servicemanager.LogInfoMsg("RoXX Windows service starting")
            run_web_server(stop_event=self.stop_event)
            servicemanager.LogInfoMsg("RoXX Windows service stopped")


def main() -> None:
    if win32serviceutil is None:
        raise SystemExit(
            "Windows service support requires pywin32 and is only available on Windows builds."
        )
    win32serviceutil.HandleCommandLine(RoXXWindowsService)


if __name__ == "__main__":
    main()

