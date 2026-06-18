"""The closed, code-fixed vocabularies for the event corpus (DESIGN.md §3/§4).

These are **declarations only** — no business logic, no DB access. They make an unknown
event kind or surface *unrepresentable*: there is no free-text type and no editorial,
runtime mutation. Extending either vocabulary is a deliberate code change (one enum
value), reviewed and migration-aware, never runtime data.

Per-kind meaning (which kinds require an originating impression, which set ``is_proxy``)
is validated in ``apps.signals.capture``, not here — one job per module (CLAUDE.md §5.3).
"""

from django.db import models


class EventKind(models.TextChoices):
    """The ``EngagementEvent.kind`` discriminator — exactly the five behavioral acts (§4).

    Adding a future kind (e.g. ``comment``) is one value here + one ``record_*`` wrapper in
    ``capture`` — no new table, no migration of the others (DESIGN.md §6).
    """

    CLICK_THROUGH = "click_through", "click-through"
    SUBSCRIBE = "subscribe", "subscribe"
    PAGE_REENGAGEMENT = "page_reengagement", "on-page re-engagement"
    SHARE = "share", "share"
    OFF_PLATFORM_PROXY = "off_platform_proxy", "off-platform proxy"


class Surface(models.TextChoices):
    """Where an impression was shown. ``DIGEST`` only at MVP (SC-1).

    Extensible by adding a value (``app_page``, ``feed``) with no migration to the others
    (DESIGN.md §4) — the impression schema does not change per surface.
    """

    DIGEST = "digest", "weekly digest"
