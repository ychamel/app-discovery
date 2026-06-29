"""The objective intake gate — the five fixed floors and their reviewer wording.

This module is the *structural* guarantee behind AC6/R1 (DESIGN.md §6): a reviewer may
only reject an app by naming one of the five **objective floors** below. There is no
"other" / "low-quality" / "not-for-us" value anywhere in ``Criterion``, so a *taste*
rejection cannot be recorded — it is unrepresentable in the decision shape, not merely
discouraged.

The floors are product-fixed (vision §5.5), so they live in **code** (type-safe, no
migration to read them, no editorial mutation path). The *set* of floors changes only by
a deliberate code change. Reviewer-facing wording lives in ``CHECKLIST`` so editing the
"what to check" text is a one-file change.

This module holds **no business logic and no DB access** — pure declaration (one job).
The write/lifecycle services (T-05/T-06) and the review surfaces (T-10/T-12) consume it.
"""

from django.db import models

from apps.core import config


class Criterion(models.TextChoices):
    """The five fixed objective floors an app must clear to be catalogued (AC5).

    Acceptance requires **all five** to pass; a rejection names **≥1** failed floor.
    There is deliberately **no catch-all value** — that absence is what makes a taste
    rejection unrepresentable (AC6/R1, DESIGN.md §6b).
    """

    WORKS = "works", "Reachable & functional"
    NOT_SPAM = "not_spam", "Not malware or spam"
    NOT_DUPLICATE = "not_duplicate", "Not a duplicate of a catalogued app"
    HONEST = "honest_metadata", "Metadata honestly describes the app"
    POLICY = "policy", "Meets basic platform policy"


# Reviewer-facing "what to check" wording for each floor (OQ-2 deliverable, DESIGN.md §6).
# Every Criterion member must have a non-empty entry — test-enforced, so no floor ever
# ships without guidance. Editing this text is a one-file change.
CHECKLIST: dict[str, str] = {
    Criterion.WORKS: (
        "Open the URL. The app loads over http(s) and its core function actually works "
        "— not a parked domain, a 404, or a blank page."
    ),
    Criterion.NOT_SPAM: (
        "The app is not malware, phishing, or spam — no deceptive downloads, credential "
        "traps, or content that exists only to drive ads/SEO."
    ),
    Criterion.NOT_DUPLICATE: (
        "The app is not a duplicate of one already catalogued. The queue flags how many "
        "other apps share this URL — confirm this is a distinct app, not a re-submission."
    ),
    Criterion.HONEST: (
        "The name and description honestly describe what the app does — no misleading "
        "claims, bait, or metadata that does not match the running app."
    ),
    Criterion.POLICY: (
        "The app meets basic platform policy — nothing illegal, no adult/abusive content, "
        "and within the kind of web app this catalogue accepts."
    ),
}


# The core floor inputs whose edit on an *accepted* app **always** forces re-review (AC8): a
# change to any of these can break a floor (honest-metadata / works), so the app returns to
# ``pending`` until re-reviewed. These are never relaxable — they are the intake floor itself.
_CORE_GATE_FIELDS: frozenset[str] = frozenset(
    {"name", "description", "url", "tags", "media"}
)


def gate_relevant_fields() -> frozenset[str]:
    """The fields whose edit on an ACCEPTED app forces re-review (D-14b / APR-DESIGN-2).

    The core floor inputs (``_CORE_GATE_FIELDS``) are **always** gated; the new public-claim
    marketing fields (tagline/deep_dive/facets/demo_clip) are gated **by config**
    (``config.app_page_gated_fields()``, default all on) so the re-review policy for them can
    be tuned from observed deployment behaviour without a code change. This is the **one**
    source of truth for the policy — ``edit_app`` calls it, never a hardcoded set.
    """
    return _CORE_GATE_FIELDS | config.app_page_gated_fields()
