"""Apply the vocabulary seed file idempotently (DESIGN.md §6, T-06).

Reads ``apps/taxonomy/seed/vocabulary.yaml`` (or ``--file``) and upserts it by ``slug``
through the write service only — never the ORM directly, so every invariant holds. The
whole apply runs in one transaction: a malformed file or a bad reference aborts the run
and writes nothing (no partial apply). Tags removed from the file are **not** deleted;
retiring a tag is explicit (a ``retired: true`` flag), routed through ``retire_tag`` so a
dropped tag never silently breaks downstream references (AC6).

Application order is deliberate so forward references resolve:
  1. upsert clusters,
  2. upsert tags (create/update fields + membership; no lifecycle change yet),
  3. apply explicit retirements (successors now exist and can be validated).
"""

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.taxonomy import services
from apps.taxonomy.errors import TaxonomyError
from apps.taxonomy.models import Cluster, Tag

DEFAULT_SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "vocabulary.yaml"


class Command(BaseCommand):
    help = "Idempotently apply the taxonomy vocabulary seed file (DESIGN.md §6)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(DEFAULT_SEED_FILE),
            help="Path to the vocabulary YAML file (defaults to the packaged seed).",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        clusters_spec, tags_spec = _load_and_validate(path)
        try:
            with transaction.atomic():
                clusters = self._apply_clusters(clusters_spec)
                tags = self._apply_tags(tags_spec, clusters)
                self._apply_retirements(tags_spec, tags)
                self._assert_integrity()
        except TaxonomyError as exc:
            # A write-service invariant rejected the file — abort, write nothing.
            raise CommandError(f"Seed aborted: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed applied: {len(clusters)} clusters, {len(tags)} tags (from {path})."
            )
        )

    # --- Application passes (each calls services only) -----------------------
    def _apply_clusters(self, clusters_spec: list[dict]) -> dict[str, Cluster]:
        registry: dict[str, Cluster] = {}
        for spec in clusters_spec:
            slug, name = spec["slug"], spec["name"]
            description = spec.get("description", "")
            existing = Cluster.objects.filter(slug=slug).first()
            if existing is None:
                cluster = services.add_cluster(slug, name, description=description)
            else:
                cluster = services.update_cluster(existing, name=name, description=description)
            registry[slug] = cluster
        return registry

    def _apply_tags(
        self, tags_spec: list[dict], clusters: dict[str, Cluster]
    ) -> dict[str, Tag]:
        registry: dict[str, Tag] = {}
        for spec in tags_spec:
            slug, label = spec["slug"], spec["label"]
            definition = spec.get("definition", "")
            members = _resolve_clusters(spec, clusters)
            existing = Tag.objects.filter(slug=slug).first()
            if existing is None:
                tag = services.add_tag(slug, label, clusters=members, definition=definition)
            else:
                tag = services.update_tag(
                    existing, label=label, clusters=members, definition=definition
                )
            registry[slug] = tag
        return registry

    def _apply_retirements(self, tags_spec: list[dict], tags: dict[str, Tag]) -> None:
        for spec in tags_spec:
            if not spec.get("retired", False):
                continue
            tag = tags[spec["slug"]]
            successor = _resolve_successor(spec, tags)
            services.retire_tag(tag, replaced_by=successor)

    def _assert_integrity(self) -> None:
        report = services.check_integrity()
        if not report.is_clean:
            orphans = [t.slug for t in report.orphan_active_tags]
            raise CommandError(
                "Seed produced integrity violations "
                f"(orphan active tags={orphans}, duplicate labels={report.duplicate_labels})."
            )


# --- Parsing & validation (fail loud, no partial apply) ----------------------
def _load_and_validate(path: Path) -> tuple[list[dict], list[dict]]:
    if not path.exists():
        raise CommandError(f"Seed file not found: {path}")
    try:
        document = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise CommandError(f"Seed file is not valid YAML: {exc}") from exc

    if not isinstance(document, dict):
        raise CommandError("Seed file must be a mapping with 'clusters' and 'tags' keys.")

    clusters_spec = document.get("clusters") or []
    tags_spec = document.get("tags") or []
    _validate_clusters(clusters_spec)
    _validate_tags(tags_spec)
    return clusters_spec, tags_spec


def _validate_clusters(clusters_spec) -> None:
    if not isinstance(clusters_spec, list):
        raise CommandError("'clusters' must be a list.")
    for index, spec in enumerate(clusters_spec):
        where = f"clusters[{index}]"
        _require_keys(spec, ("slug", "name"), where)


def _validate_tags(tags_spec) -> None:
    if not isinstance(tags_spec, list):
        raise CommandError("'tags' must be a list.")
    for index, spec in enumerate(tags_spec):
        where = f"tags[{index}]"
        _require_keys(spec, ("slug", "label"), where)
        members = spec.get("clusters")
        if not isinstance(members, list) or not members:
            raise CommandError(f"{where} ({spec.get('slug')!r}) must list ≥1 cluster slug.")


def _require_keys(spec, keys: tuple[str, ...], where: str) -> None:
    if not isinstance(spec, dict):
        raise CommandError(f"{where} must be a mapping.")
    for key in keys:
        if not spec.get(key):
            raise CommandError(f"{where} is missing required key {key!r}.")


def _resolve_clusters(spec: dict, clusters: dict[str, Cluster]) -> list[Cluster]:
    members = []
    for cluster_slug in spec["clusters"]:
        if cluster_slug not in clusters:
            raise CommandError(
                f"Tag {spec['slug']!r} references unknown cluster {cluster_slug!r}."
            )
        members.append(clusters[cluster_slug])
    return members


def _resolve_successor(spec: dict, tags: dict[str, Tag]) -> Tag | None:
    successor_slug = spec.get("replaced_by")
    if successor_slug is None:
        return None
    if successor_slug not in tags:
        raise CommandError(
            f"Tag {spec['slug']!r} is retired into unknown successor {successor_slug!r}."
        )
    return tags[successor_slug]
