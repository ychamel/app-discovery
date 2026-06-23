"""One-off backfill of the open-search-browse columns for existing apps (T-03, DESIGN §5a/§5b).

Populates the two additive columns added in 0002 for apps already in the catalogue, so the
new discovery read (T-05) sees real data the moment it goes live:

  * ``accepted_at`` ← the **latest** ``ReviewDecision(outcome=accepted).created_at`` (the real
    acceptance time the ordering key means); a never-accepted app stays ``NULL``.
  * ``search_vector`` ← the shared ``catalog.services._search_vector_expr()`` (imported, not
    re-stated, so the formula stays single-sourced with the write path).

Bounded by current catalogue size, run once. Reversible: the reverse sets both columns back
to ``NULL`` (a safe no-op for a fresh DB, mirroring how the forward write computes them).
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery

from apps.catalog.services import _search_vector_expr


def backfill(apps, schema_editor):
    App = apps.get_model("catalog", "App")
    ReviewDecision = apps.get_model("catalog", "ReviewDecision")

    latest_accept = (
        ReviewDecision.objects.filter(app=OuterRef("pk"), outcome="accepted")
        .order_by("-created_at")
        .values("created_at")[:1]
    )
    # accepted_at = the most recent accept decision's time, or NULL where there is none.
    App.objects.update(accepted_at=Subquery(latest_accept))
    # search_vector = the same name(A)+description(B) formula the write path maintains.
    App.objects.update(search_vector=_search_vector_expr())


def clear(apps, schema_editor):
    App = apps.get_model("catalog", "App")
    App.objects.update(accepted_at=None, search_vector=None)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_app_accepted_at_app_search_vector_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, clear),
    ]
