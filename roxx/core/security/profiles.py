"""Environment-driven security profiles for RoXX deployments."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SecurityProfile:
    name: str
    secure_cookies: bool
    hsts: bool
    require_persistent_secret: bool
    content_security_policy: str

    @classmethod
    def from_env(cls) -> "SecurityProfile":
        name = os.getenv("ROXX_SECURITY_PROFILE", "standard").strip().lower()
        if name not in {"development", "standard", "production"}:
            raise ValueError("ROXX_SECURITY_PROFILE must be development, standard, or production")

        production = name == "production"
        return cls(
            name=name,
            secure_cookies=_flag("ROXX_SECURE_COOKIES", production),
            hsts=_flag("ROXX_HSTS", production),
            require_persistent_secret=production,
            content_security_policy=os.getenv(
                "ROXX_CONTENT_SECURITY_POLICY",
                "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; connect-src 'self' ws: wss:",
            ),
        )

    def validate(self, secret_key: str | None) -> None:
        if self.require_persistent_secret and not secret_key:
            raise RuntimeError("ROXX_SECRET_KEY is required by the production security profile")
