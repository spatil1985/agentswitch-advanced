"""Local-only platform login with a token cache. Never used on the course platform.

The eval harness never logs in: on the platform the course runner hands it a token. On your own computer,
scripts/run_local.py (and the probe and sync scripts) call get_token(), which:
  1. reuses the cached token in TOKEN_CACHE_DIR/<system>.json if one GET /api/auth/me still accepts it;
  2. otherwise logs in ONCE with AS_EMAIL and AS_<SYSTEM>_PASSWORD from .env and caches the new token;
  3. stops on a refused login, without retrying (ten wrong tries lock the account for the whole team).

Tokens last about 7 days, so the password is used about once a week per system.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx2
from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

SEAT_DIR = Path(__file__).resolve().parent.parent
SYSTEMS = ("suryodaya", "keystone")
HTTP_TIMEOUT = httpx2.Timeout(60, read=120)


class LocalSettings(BaseSettings):
    """The local-only part of .env: who we are on each system, and where tokens are cached."""

    model_config = SettingsConfigDict(env_file=SEAT_DIR / ".env", extra="ignore", env_ignore_empty=True)
    as_email: str
    as_suryodaya_password: SecretStr
    as_keystone_password: SecretStr
    as_suryodaya_url: str
    as_keystone_url: str
    token_cache_dir: Path = Path(".cache/tokens")

    def url(self, system: str) -> str:
        base: str = getattr(self, f"as_{system}_url")
        return base.rstrip("/")

    def password(self, system: str) -> str:
        secret: SecretStr = getattr(self, f"as_{system}_password")
        return secret.get_secret_value()

    def cache_file(self, system: str) -> Path:
        folder = (
            self.token_cache_dir if self.token_cache_dir.is_absolute() else SEAT_DIR / self.token_cache_dir
        )
        return folder / f"{system}.json"


class LoginFailed(Exception):
    """The platform refused our login. We never retry, to avoid locking the account."""


def load_local_settings() -> LocalSettings | None:
    """Read .env. On a problem, print the missing variable names only, never their values."""
    try:
        return LocalSettings()  # values come from .env
    except ValidationError as e:
        names = sorted({"_".join(str(part) for part in err["loc"]).upper() for err in e.errors()})
        print(f"Missing or invalid in .env: {', '.join(names)} (see .env.example)", file=sys.stderr)
        return None


async def login(http: httpx2.AsyncClient, base: str, email: str, password: str, system: str) -> str:
    """Log in once. Raises LoginFailed (never retries) if the platform refuses."""
    reply = await http.post(f"{base}/api/auth/login", json={"email": email, "password": password})
    if reply.status_code != 200:
        raise LoginFailed(f"{system}: login refused with HTTP {reply.status_code}: {reply.text[:200]}")
    token = reply.json().get("token")
    if not isinstance(token, str) or not token:
        raise LoginFailed(f"{system}: login reply had no token")
    return token


async def token_works(http: httpx2.AsyncClient, base: str, token: str) -> bool:
    reply = await http.get(f"{base}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    return reply.status_code == 200


def _read_cache(path: Path, email: str) -> str | None:
    try:
        cached = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    token = cached.get("token") if cached.get("email") == email else None
    return token if isinstance(token, str) and token else None


def _write_cache(path: Path, email: str, token: str) -> None:
    """Write the token readable only by you (mode 600), replacing the old file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"email": email, "token": token, "obtained_at": datetime.now(UTC).isoformat()}, f)
    os.replace(tmp, path)


async def get_token(settings: LocalSettings, system: str) -> str:
    """A working token for this system: the cached one if it still works, else one fresh login."""
    base, path = settings.url(system), settings.cache_file(system)
    async with httpx2.AsyncClient(timeout=HTTP_TIMEOUT) as http:
        cached = _read_cache(path, settings.as_email)
        if cached and await token_works(http, base, cached):
            return cached
        token = await login(http, base, settings.as_email, settings.password(system), system)
    _write_cache(path, settings.as_email, token)
    return token
