from django.apps import AppConfig


class InterestsConfig(AppConfig):
    """Interest profile: the declared interest tags a signed-in user cares about.

    Owns one mutable table (``interests_interest``) — one row per (user, declared
    ``Tag.id``). The *interest profile* is the SET of a user's rows; there is no parent
    profile row, so an empty profile is the structural default (interest-profile DESIGN
    §4.1, AC6). The ``user`` FK **CASCADE**s: a declaration is mutable preference state,
    removed with the account (AC9) with no edit to ``accounts``.

    Unlike the near-twin ``apps.subscriptions``, this app emits **no D-7 event** and does
    **not** import ``signals.capture`` (IP-5) — declaration is preference state, not
    behavior. Computes **no** score: scoring is the future matcher's job (AC8).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.interests"
    label = "interests"
