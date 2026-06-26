# FEATURE_BRIEF — embeddable-update-widget

_Status: pending — Stage 1 (Product Analyst) authors this._

> **Coordinator seed (2026-06-26).** Activated by the **developer-wedge pivot**
> ([global D-10](../../DECISIONS.md)). This is the **core audience-capture mechanism** of
> the wedge: an embeddable "what's new" widget a developer drops **inside their own app**,
> surfacing that app's published update notices and a path back to the app's page on the
> platform — so each developer's existing users get pulled onto the platform (the
> bring-your-own-audience engine that fills the platform without acquiring users directly).
>
> **Grounding (read these first):** the `developer-updates` notice contract — the **AS-3
> `Notice` DTO** in [apps/subscriptions/notices.py](../../apps/subscriptions/notices.py)
> and `apps/updates/` (the producer); the `app-pages` destination ([apps/pages/](../../apps/pages/));
> the **D-6** catalogued-app identity. Per **[D-10](../../DECISIONS.md)** and the §4.1 gate,
> widget impressions/click-throughs are a **non-curated surface** that must **not** confer
> **D-8** curated-rating eligibility — make that boundary explicit. Whether the widget→platform
> click-through emits any (non-curated) D-7 signal at MVP is an open Stage-2 question.
>
> Product Analyst: read the request, vision **§5.4 (revised)** + **§5.6 (revised)**, and
> global **D-9/D-10**, then author the brief.
