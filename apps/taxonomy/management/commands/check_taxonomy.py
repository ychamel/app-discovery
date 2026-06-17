"""Assert vocabulary integrity as a CI/ops gate (DESIGN.md §6/§10, T-07).

Runs ``services.check_integrity()`` and reports the three conditions it finds:
  * **orphan active tags** (active + zero clusters) — a violation of the ≥1-cluster
    invariant no single DB constraint can express (DESIGN.md §13);
  * **duplicate labels** — a non-redundancy violation (AC1);
  * **empty clusters** — a *warning* only (a cluster may legitimately empty as its tags
    retire; it is never auto-deleted — AC8).

On any violation it increments ``taxonomy_integrity_violation`` and exits **non-zero**, so
it is usable as a deploy/CI gate. A clean vocabulary exits 0.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core import observability
from apps.taxonomy import services


class Command(BaseCommand):
    help = "Check taxonomy integrity; non-zero exit on a violation (DESIGN.md §6)."

    def handle(self, *args, **options):
        report = services.check_integrity()

        for cluster in report.empty_clusters:
            self.stdout.write(
                self.style.WARNING(f"WARNING: cluster {cluster.slug!r} has no tags.")
            )

        if report.is_clean:
            self.stdout.write(self.style.SUCCESS("Taxonomy integrity OK."))
            return

        for tag in report.orphan_active_tags:
            self.stderr.write(f"VIOLATION: active tag {tag.slug!r} is in zero clusters.")
        for label in report.duplicate_labels:
            self.stderr.write(f"VIOLATION: duplicate label {label!r}.")

        observability.increment(observability.TAXONOMY_INTEGRITY_VIOLATION)
        raise CommandError(
            f"Taxonomy integrity check failed: "
            f"{len(report.orphan_active_tags)} orphan active tag(s), "
            f"{len(report.duplicate_labels)} duplicate label(s)."
        )
