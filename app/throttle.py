"""Login throttle: per client address, with a doubling lockout.

The app runs as one gunicorn worker (see the Dockerfile), so an in-process
table is shared by every request. A restart forgets it, which is fine: the
point is to make guessing the shared password slow, not to keep a ledger.
"""
import ipaddress
import os
import threading
import time

from flask import request

# A few typos are free; after that each further miss doubles the wait.
FREE_FAILURES = 5
BASE_LOCKOUT_SECONDS = 30
MAX_LOCKOUT_SECONDS = 15 * 60
# A client with no misses for this long starts over.
FORGET_AFTER_SECONDS = 60 * 60
# Bounds memory if someone sprays from many addresses.
MAX_TRACKED = 10_000

_lock = threading.Lock()
# address -> (failure count, time of last failure, locked until)
_failures: dict[str, tuple[int, float, float]] = {}


def _trusted_proxies():
    """Addresses whose X-Forwarded-For we believe. In production that is
    Caddy on edge; anyone else reaching port 8854 directly could forge it."""
    raw = os.environ.get("SPEEDHIVE_TRUSTED_PROXIES", "")
    nets = []
    for part in raw.replace(",", " ").split():
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            continue
    return nets


def client_address():
    """The address to throttle on. Behind a trusted proxy that is the last
    X-Forwarded-For entry (the one the proxy itself saw and appended);
    otherwise the socket peer."""
    peer = request.remote_addr or ""
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        return peer
    if any(peer_ip in net for net in _trusted_proxies()):
        forwarded = request.headers.get("X-Forwarded-For", "")
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        if hops:
            return hops[-1]
    return peer


def retry_after(address, now=None):
    """Seconds until this address may try again, or 0."""
    now = time.time() if now is None else now
    with _lock:
        entry = _failures.get(address)
    if not entry:
        return 0
    return max(0, int(entry[2] - now + 0.999))


def record_failure(address, now=None):
    now = time.time() if now is None else now
    with _lock:
        count, last, _until = _failures.get(address, (0, now, 0.0))
        if now - last > FORGET_AFTER_SECONDS:
            count = 0
        count += 1
        until = 0.0
        if count > FREE_FAILURES:
            wait = BASE_LOCKOUT_SECONDS * 2 ** (count - FREE_FAILURES - 1)
            until = now + min(wait, MAX_LOCKOUT_SECONDS)
        _failures[address] = (count, now, until)
        if len(_failures) > MAX_TRACKED:
            _prune(now)


def record_success(address):
    with _lock:
        _failures.pop(address, None)


def reset():
    with _lock:
        _failures.clear()


def _prune(now):
    stale = [a for a, (_c, last, until) in _failures.items()
             if now - last > FORGET_AFTER_SECONDS and until <= now]
    for a in stale:
        del _failures[a]
    # Still too many: drop the oldest so the table stays bounded.
    if len(_failures) > MAX_TRACKED:
        for a, _ in sorted(_failures.items(), key=lambda kv: kv[1][1])[: len(_failures) - MAX_TRACKED]:
            del _failures[a]
