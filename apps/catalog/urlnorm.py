"""The single rule for "these two URLs are the same app" (DESIGN.md §3/§6c).

``normalize_url`` canonicalizes a URL so two submissions that differ only cosmetically
(scheme case, host case, a default port, a trailing slash) map to the **same** string,
while genuinely different paths or hosts map to **different** strings. The result is
stored as ``App.normalized_url`` and keys the duplicate **signal** (``apps_sharing_url``,
T-07).

It is a **signal, not a constraint** (SI-2 — review is manual): this function decides
equality only; it never rejects a URL and never reaches the database. URL *well-formedness*
is validated separately at the write boundary (T-05).

Determinism matters more than cleverness here: the rules below are intentionally minimal
and conservative — collapse only differences that never change which app is served, and
leave everything else (query string, fragment, path case, percent-encoding) untouched so
two distinct apps are never merged.
"""

from urllib.parse import urlsplit, urlunsplit

# Ports that carry no meaning for their scheme — stripping them cannot change the target.
_DEFAULT_PORTS = {"http": "80", "https": "443"}


def normalize_url(raw: str) -> str:
    """Return the canonical form of ``raw`` for duplicate detection (DESIGN.md §6c).

    Idempotent: ``normalize_url(normalize_url(x)) == normalize_url(x)``. Canonicalizes:
      * scheme — lowercased;
      * host — lowercased, a default port for the scheme removed;
      * path — a single trailing slash dropped (so ``/x`` and ``/x/`` match), root kept as ``/``.

    Host variants like ``www.`` are intentionally **not** collapsed: ``www.example.com``
    and ``example.com`` can serve different apps, so they stay distinct (the manual
    reviewer remains the duplicate authority — SI-2). This stays faithful to the four
    equivalence classes the design fixes (DESIGN.md §6c).

    The query and fragment are preserved as-is — two URLs differing in query genuinely may
    serve different apps, so they must not collapse.
    """
    parts = urlsplit(raw.strip())

    scheme = parts.scheme.lower()
    host = _canonical_host(parts.hostname, parts.port, scheme)
    # Preserve userinfo if present (rare for app URLs) without altering it.
    netloc = f"{parts.username}@{host}" if parts.username else host
    path = _canonical_path(parts.path)

    return urlunsplit((scheme, netloc, path, parts.query, parts.fragment))


def _canonical_host(hostname: str | None, port: int | None, scheme: str) -> str:
    """Lowercase the host and drop a default port for the scheme."""
    if not hostname:
        return ""
    host = hostname.lower()
    if port is not None and str(port) != _DEFAULT_PORTS.get(scheme):
        return f"{host}:{port}"
    return host


def _canonical_path(path: str) -> str:
    """Drop a single trailing slash, but keep the root path as ``/``."""
    if path in ("", "/"):
        return "/"
    return path.rstrip("/") or "/"
