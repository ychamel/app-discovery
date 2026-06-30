"""The three thin HTTP views for interests (DESIGN.md §5.3/§6/§8).

Mirrors the pages/ratings/subscriptions house pattern: each view **parses input, calls a
service/selector, and redirects or renders** — it holds no business logic and no direct ORM
access (the picker view-model is assembled from ``taxonomy``/``selectors`` reads only).

Own-data-only is **structural** (DESIGN §11): no interest id appears in any URL. A
declaration is addressed by ``request.user`` + ``tag_id``, so a user can only ever touch
their own profile (no IDOR). All three routes are ``login_required``; the mutations are POST
+ CSRF.

The failure split (DESIGN §9): the **write** fails loud inside ``services`` where correctness
depends on it, and the *view* surfaces a validation reject as a re-rendered picker + 400
(durable state honest — no partial set, AC2) or a DB failure as a try-again message; the
**picker read** fails soft so a fault never 500s the page (AC6 degraded state).
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core import config, observability
from apps.interests import selectors, services
from apps.interests.errors import InterestValidationError
from apps.taxonomy import selectors as taxonomy

logger = logging.getLogger(__name__)

_SAVE_FAILED_MESSAGE = "Couldn't save, please try again."
_INVALID_MESSAGE = "That selection isn't valid — please try again."
_SAVED_MESSAGE = "Saved your interests."


@login_required
@require_http_methods(["GET"])
def picker(request):
    """GET interests/ — the cluster-grouped active picker (AC1/AC5/AC6).

    Fail-soft (DESIGN §9): a taxonomy/selector read error renders a degraded "couldn't load"
    page (never a 500) + ``INTEREST_PICKER_DEGRADED``.
    """
    try:
        context = _build_picker_context(request.user)
    except Exception:
        observability.increment(observability.INTEREST_PICKER_DEGRADED)
        logger.warning("interest picker degraded", exc_info=True)
        return render(request, "interests/picker.html", {"degraded": True}, status=200)
    return render(request, "interests/picker.html", context)


@login_required
@require_http_methods(["POST"])
def save(request):
    """POST interests/save — set the user's interests, then PRG back to the picker (AC1/AC4).

    A validation reject re-renders the picker with the message + **400** (no partial set,
    AC2). A DB write failure surfaces a try-again message and re-renders (the save rolled
    back — durable state honest). Success → PRG with a success message.
    """
    submitted_ids = request.POST.getlist("tag_id")
    try:
        services.set_interests(request.user, submitted_ids)
    except InterestValidationError:
        context = _build_picker_context(request.user)
        context["error"] = _INVALID_MESSAGE
        return render(request, "interests/picker.html", context, status=400)
    except Exception:
        logger.warning("interest save failed", exc_info=True)
        context = _build_picker_context(request.user)
        context["error"] = _SAVE_FAILED_MESSAGE
        return render(request, "interests/picker.html", context, status=200)
    messages.success(request, _SAVED_MESSAGE)
    return redirect("interests:picker")


@login_required
@require_http_methods(["POST"])
def clear(request):
    """POST interests/clear — remove all the user's interests, then PRG (AC9)."""
    services.clear_interests(request.user)
    return redirect("interests:picker")


# --- View-model assembly (reads only — no write, no direct ORM) --------------
def _build_picker_context(user) -> dict:
    """Assemble the picker view-model from the active vocabulary + the user's resolved set.

    Pre-checks a tag iff its id is in the user's resolved declared set (``declared_tags``).
    The suggested-minimum nudge is **copy only** (IP-3) — it never blocks a save.
    """
    declared_ids = {tag.id for tag in selectors.declared_tags(user)}
    clusters = _cluster_rows(declared_ids)
    declared_count = len(declared_ids)
    return {
        "clusters": clusters,
        "has_any_tag": any(row["tags"] for row in clusters),
        "declared_count": declared_count,
        "suggested_minimum": config.interest_suggested_minimum(),
        "degraded": False,
    }


def _cluster_rows(declared_ids: set) -> list[dict]:
    """Each cluster with its active tags as (tag, checked) pairs — the AC5 render shape."""
    seen_tags = set()
    rows = []
    for cluster in taxonomy.list_clusters():
        tags = []
        for tag in cluster.tags.all():
            if tag.id not in seen_tags:
                seen_tags.add(tag.id)
                tags.append({"tag": tag, "checked": tag.id in declared_ids})
        rows.append({"cluster": cluster, "tags": tags})
    return rows
