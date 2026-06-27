"""The widget source-marker codec + credit logic (widget-conversion-attribution DESIGN §3/§5.1).

This is the **only** module that knows the `widget_src` cookie format. It carries a single fact —
*which app's widget click-through this browser most recently passed through* — first-party from the
click 302 (``set_marker``) to a later conversion (``attribute_follow`` / ``attribute_account``),
where it credits one aggregate conversion to that **source app** and never to a person.

Three properties hold by construction (DESIGN §3, §8):

  * **No PII (AC4).** The signed payload is exactly ``{v, src, credited}`` — a payload version, a
    public source ``App.id``, and the set of conversion kinds already credited from this marker.
    There is no person, session, IP, or device field; there is nowhere to put one.
  * **Tamper-evident + windowed (AC2).** The payload is signed with ``django.core.signing`` (HMAC
    over ``SECRET_KEY`` — tamper-evident, not secret) and carries the signer's timestamp, so a
    forged/edited marker fails to load and a marker older than the configured window is rejected as
    expired. A missing / malformed / version-skewed / expired / wrong-app marker is a **normal "no
    source" outcome** (a no-op + an ops counter), never an error to the visitor.
  * **Last-touch + dedup (WCA-2 / R4).** Each click-through *overwrites* the marker (last-touch).
    A credit adds its kind to ``credited`` and re-issues the cookie with the **remaining** window
    so the window stays anchored to the original click — and a repeat of the same kind in the same
    browser within the window is a silent no-op.

A DB write failure in the writer **propagates** to the caller, which wraps it fail-soft (the view
hooks, T-05/T-06) so a conversion miss never breaks a redirect, a follow, or a registration.
Imports nothing from ``apps.signals`` (the firewall — AST-proven in ``tests/test_imports.py``).
"""

import time
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.core import signing

from apps.core.config import widget_attribution_window_days
from apps.core.observability import (
    WIDGET_CONVERSION_ATTRIBUTED,
    WIDGET_CONVERSION_EXPIRED,
    WIDGET_CONVERSION_NO_SOURCE,
    increment,
)
from apps.widget.attribution import record_widget_conversion
from apps.widget.kinds import WidgetConversionKind

COOKIE_NAME = "widget_src"
# Namespaces the signature so a `widget_src` value can never be confused with any other signed
# cookie in the app (django.core.signing best practice).
_SALT = "apps.widget.source"
# The payload schema version. An unknown version is treated as "no marker" (forward-compatible):
# a future schema can change shape without a stale marker being mis-read.
_VERSION = 1
_SECONDS_PER_DAY = 86400

_VALID_KINDS = frozenset(WidgetConversionKind.values)


@dataclass(frozen=True)
class _Marker:
    """A loaded, in-window source marker — the source app and what it has already credited.

    ``raw`` is retained so the signature age can be read on the re-issue path (DESIGN §3.4) without
    re-deserializing the payload.
    """

    raw: str
    src: str  # the source App.id, a UUID string we ourselves signed
    credited: list[str]


def _window_seconds() -> int:
    """The attribution window in seconds — the single source of truth, from config (WCA-2)."""
    return widget_attribution_window_days() * _SECONDS_PER_DAY


def set_marker(response, source_app_id: UUID) -> None:
    """Set/refresh the first-party source cookie on ``response`` (called from the click 302).

    Signs a fresh marker for ``source_app_id`` and writes ``widget_src``. **Overwrites** any prior
    marker, which is what makes attribution last-touch (DESIGN §3.4). Pure cookie write — no DB.
    """
    _write_marker(response, src=str(source_app_id), credited=[], max_age=_window_seconds())


def attribute_follow(request, response, *, followed_app_id: UUID) -> None:
    """Credit a FOLLOW conversion iff the live marker's ``src`` is ``followed_app_id`` and FOLLOW is
    not already credited (DESIGN §5.1).

    No marker / expired / wrong app / already-credited → a no-op with the matching ops counter.
    Raises only if the conversion writer raises (a DB error); the caller wraps that fail-soft.
    """
    marker = _load_live_marker(request)
    if marker is None:
        return  # _load_live_marker already counted NO_SOURCE / EXPIRED
    if marker.src != str(followed_app_id):
        # A live marker exists, but for a different app — this follow had no applicable widget
        # source. From this conversion's standpoint that is a no-source outcome (M3 denominator).
        increment(WIDGET_CONVERSION_NO_SOURCE)
        return
    _credit(response, marker, WidgetConversionKind.FOLLOW)


def attribute_account(request, response) -> None:
    """Credit an ACCOUNT conversion for the live marker's ``src`` iff ACCOUNT is not already
    credited (DESIGN §5.1).

    Unlike a follow this is **not** app-scoped — an account is platform-wide, so any live marker
    credits its source app. Same no-source / dedup / fail-soft contract as ``attribute_follow``.
    """
    marker = _load_live_marker(request)
    if marker is None:
        return
    _credit(response, marker, WidgetConversionKind.ACCOUNT)


def _credit(response, marker: _Marker, kind: str) -> None:
    """Record one conversion of ``kind`` for ``marker.src``, dedup, and re-issue the cookie.

    Dedup (R4) is silent — a repeat of an already-credited kind is not a coverage miss, so it emits
    no counter. The re-issue carries the **remaining** window (DESIGN §3.4), keeping the window
    anchored to the original click rather than resetting it.
    """
    if kind in marker.credited:
        return  # already credited from this marker in this browser — per-marker dedup no-op
    # Raises on a DB error; attribute_* let it propagate so the view hook handles it fail-soft.
    record_widget_conversion(UUID(marker.src), kind)
    increment(WIDGET_CONVERSION_ATTRIBUTED, kind=kind)

    remaining = _window_seconds() - _signature_age_seconds(marker.raw)
    if remaining <= 0:
        return  # window already elapsed (it was in-window when loaded; nothing to re-issue)
    _write_marker(
        response,
        src=marker.src,
        credited=[*marker.credited, kind],
        max_age=int(remaining),
    )


def _load_live_marker(request) -> _Marker | None:
    """Return the in-window marker on ``request``, or ``None`` (counting why) on any miss.

    Every "no usable marker" reason is a normal outcome, not an error: a missing / malformed /
    tampered / version-skewed marker counts NO_SOURCE; one past the window counts EXPIRED.
    """
    raw = request.COOKIES.get(COOKIE_NAME)
    if not raw:
        increment(WIDGET_CONVERSION_NO_SOURCE)
        return None
    try:
        payload = signing.loads(raw, salt=_SALT, max_age=_window_seconds())
    except signing.SignatureExpired:
        increment(WIDGET_CONVERSION_EXPIRED)  # a marker existed but was outside the window (AC2)
        return None
    except signing.BadSignature:
        increment(WIDGET_CONVERSION_NO_SOURCE)  # tampered / malformed → treated as no source
        return None
    if not _is_valid_payload(payload):
        increment(WIDGET_CONVERSION_NO_SOURCE)  # version skew / wrong shape → no source
        return None
    return _Marker(raw=raw, src=payload["src"], credited=list(payload["credited"]))


def _is_valid_payload(payload: object) -> bool:
    """Whether a decoded payload is a current-version, well-formed source marker.

    Anything else (an unknown version, a non-UUID ``src``, an off-vocabulary ``credited`` entry) is
    a "no source" outcome — never trusted, never an error.
    """
    if not isinstance(payload, dict) or payload.get("v") != _VERSION:
        return False
    src = payload.get("src")
    if not isinstance(src, str) or not _is_uuid(src):
        return False
    credited = payload.get("credited")
    if not isinstance(credited, list) or any(k not in _VALID_KINDS for k in credited):
        return False
    return True


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _signature_age_seconds(raw: str) -> float:
    """Seconds since ``raw`` was signed, read from the signer's own timestamp (DESIGN §3.4).

    ``signing.loads`` validates the timestamp against ``max_age`` but discards it, so we strip the
    HMAC and parse the timestamp the signer appended. Called only on the re-issue path, on a value
    whose integrity ``_load_live_marker`` already verified.
    """
    signer = signing.TimestampSigner(salt=_SALT)
    timestamped = signing.Signer.unsign(signer, raw)  # "<payload><sep><base62 timestamp>"
    _, b62_timestamp = timestamped.rsplit(signer.sep, 1)
    return time.time() - signing.b62_decode(b62_timestamp)


def _write_marker(response, *, src: str, credited: list[str], max_age: int) -> None:
    """Sign ``{v, src, credited}`` and write the ``widget_src`` cookie with the DESIGN §3.1 attrs.

    ``Secure`` follows the platform's cookie policy (``SESSION_COOKIE_SECURE`` — set off ``DEBUG``,
    so the cookie is stored over plain HTTP in local dev and required-HTTPS in production).
    ``HttpOnly`` keeps the marker out of page JS (it is never read client-side); ``SameSite=Lax``
    suffices because every post-click step is a same-site first-party request to the platform.
    """
    value = signing.dumps(
        {"v": _VERSION, "src": src, "credited": credited}, salt=_SALT
    )
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=max_age,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
        path="/",
    )
