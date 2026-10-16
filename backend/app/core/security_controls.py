"""Bounded request throttling and security events without request secrets."""
import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import socket
import threading
import time

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from app.core.config import settings

audit_logger = logging.getLogger("app.security.audit")


def client_address(scope):
    return scope.get("state", {}).get("rate_limit_client", (scope.get("client") or ("unknown", 0))[0])


def canonical_ip(value):
    address = ipaddress.ip_address(value)
    return str(getattr(address, "ipv4_mapped", None) or address)


def security_digest(purpose: str, value: str) -> str:
    """Use separate keyed identifiers; never expose credentials or client names."""
    return hmac.new(settings.secret_key.encode(), f"{purpose}\0{value}".encode(), hashlib.sha256).hexdigest()


def audit_event(event: str, *, scope=None, user_id=None, actor_id=None, reason=None):
    record = {"event": event}
    if scope is not None:
        peer = client_address(scope)
        record["client_id"] = security_digest("client", peer)
        method = scope.get("method", "")
        record["method"] = method if method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS") else "OTHER"
        route = scope.get("route")
        if route is not None:
            # Route templates are application constants, unlike raw URL paths.
            record["route"] = route.path
        user_id = user_id or scope.get("state", {}).get("audit_user_id")
    if user_id is not None:
        record["user_id"] = user_id
    if actor_id is not None:
        record["actor_id"] = actor_id
    if reason is not None:
        record["reason"] = reason
    audit_logger.info(json.dumps(record, separators=(",", ":"), sort_keys=True))


class RateLimiter:
    """Fixed windows with bounded keys; full tables reject instead of evicting."""

    def __init__(self, window_seconds=60, max_keys=4096, clock=time.monotonic):
        if window_seconds <= 0 or max_keys <= 0:
            raise ValueError("Rate-limit windows and capacity must be positive")
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self.clock = clock
        self._windows = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int) -> int:
        """Consume one request, returning zero or a positive retry delay."""
        if limit <= 0:
            raise ValueError("Rate limit must be positive")
        with self._lock:
            now = self.clock()
            expires, count = self._windows.get(key, (now + self.window_seconds, 0))
            if expires <= now:
                expires, count = now + self.window_seconds, 0
            if key not in self._windows and len(self._windows) >= self.max_keys:
                self._windows = {item: window for item, window in self._windows.items() if window[0] > now}
                if len(self._windows) >= self.max_keys:
                    return max(1, math.ceil(min(window[0] for window in self._windows.values()) - now))
            if count >= limit:
                return max(1, math.ceil(expires - now))
            self._windows[key] = (expires, count + 1)
            return 0


def check_login_limit(request: Request, username: str):
    limiter = getattr(request.app.state, "login_rate_limiter", None)
    if limiter is None:
        limiter = RateLimiter(settings.rate_limit_window_seconds)
        request.app.state.login_rate_limiter = limiter
    peer = client_address(request.scope)
    checks = (("client", peer, settings.login_client_limit),
              ("account", username.casefold(), settings.login_account_limit))
    for purpose, value, limit in checks:
        retry = limiter.check(security_digest(f"login-{purpose}", value), limit)
        if retry:
            audit_event("login.throttled", scope=request.scope, reason=purpose)
            raise HTTPException(429, "Too many sign-in attempts. Please try again later.",
                                headers={"Retry-After": str(retry), "Cache-Control": "no-store"})


class SecurityControlsMiddleware:
    """Throttle before reading bodies, accepting client IPs only from trusted proxies."""

    def __init__(self, app, api_limit=600, window_seconds=60, trusted_proxies=""):
        self.app = app
        self.api_limit = api_limit
        self.limiter = RateLimiter(window_seconds)
        self.audit_limiter = RateLimiter(window_seconds)
        self.proxy_hosts = tuple(host.strip() for host in trusted_proxies.split(",") if host.strip())
        self.proxy_addresses = set()
        self.proxy_refresh_at = 0
        self.proxy_lock = asyncio.Lock()

    async def _client_address(self, scope):
        peer = (scope.get("client") or ("unknown", 0))[0]
        try:
            peer = canonical_ip(peer)
        except ValueError:
            return peer
        if not self.proxy_hosts:
            return peer
        if time.monotonic() >= self.proxy_refresh_at:
            async with self.proxy_lock:
                if time.monotonic() >= self.proxy_refresh_at:
                    addresses = set()
                    for host in self.proxy_hosts:
                        try:
                            addresses.add(canonical_ip(host))
                        except ValueError:
                            # Only operator-configured names are resolved, never
                            # values supplied by request headers. Refresh after
                            # container restarts without trusting a whole subnet.
                            try:
                                results = await asyncio.to_thread(socket.getaddrinfo, host, None, 0, socket.SOCK_STREAM)
                                addresses.update(canonical_ip(item[4][0]) for item in results)
                            except (OSError, ValueError):
                                pass  # A failed lookup does not grant trust.
                    self.proxy_addresses = addresses
                    self.proxy_refresh_at = time.monotonic() + 60
        if peer not in self.proxy_addresses:
            return peer
        forwarded = [value for name, value in scope.get("headers", []) if name.lower() == b"x-forwarded-for"]
        if len(forwarded) == 1:
            try:
                return canonical_ip(forwarded[0].decode("ascii").strip())
            except (UnicodeError, ValueError):
                pass
        return peer

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == "/api" or path.startswith("/api/")):
            await self.app(scope, receive, send)
            return
        peer = await self._client_address(scope)
        scope.setdefault("state", {})["rate_limit_client"] = peer
        key = security_digest("client", peer)
        retry = self.limiter.check(key, self.api_limit)
        if retry:
            if self.audit_limiter.check(key, 1) == 0:
                audit_event("api.throttled", scope=scope, reason="client")
            headers = {"Retry-After": str(retry), "Cache-Control": "no-store"}
            if scope.get("http_version", "1.1") in ("1.0", "1.1"):
                headers["Connection"] = "close"
            await JSONResponse({"detail": "Too many requests. Please try again later."},
                               status_code=429, headers=headers)(scope, receive, send)
            return

        async def audited_send(message):
            if message["type"] == "http.response.start":
                status = message["status"]
                if status in (401, 403):
                    audit_event("access.denied", scope=scope, reason=str(status))
                elif scope.get("method") not in ("GET", "HEAD", "OPTIONS"):
                    audit_event("api.mutation", scope=scope, reason=str(status))
            await send(message)

        await self.app(scope, receive, audited_send)
