from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    """App subscriptions: one durable follow per user per app + one D-7 ``subscribe`` emit.

    Owns one mutable table (``subscriptions_subscription``) — the *current* follow
    relationship, created and removed but never versioned. Unlike the append-only D-7
    signals corpus (and unlike ratings' SET_NULL anonymize-on-delete), the ``user`` FK
    **CASCADE**s: a follow is live relationship state, removed with the account, while the
    already-emitted ``subscribe`` events are owned by signals and anonymize-not-purge under
    SC-10 (app-subscriptions DESIGN §2/§4). Computes **no** score.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.subscriptions"
    label = "subscriptions"
