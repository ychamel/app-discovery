from django.apps import AppConfig


class RatingsConfig(AppConfig):
    """Ratings & reviews: one editable rating per user per app + the recorded curated gate.

    Owns one mutable table (``ratings_rating``) — the deliberate contrast with the
    append-only D-7 signals corpus. It records, for every rating, whether its author was
    organically curated to the app (a DIGEST impression), but computes **no** score
    (ratings-reviews DESIGN §2/§4).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ratings"
    label = "ratings"
