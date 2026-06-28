# Staging walkthrough — suggested full-role script

This is the script **you** (the operator) follow to walk the deployed staging wedge end-to-end
as all three roles on **web + mobile**, and to record the human-judgment sign-offs and the two
verdicts (platform-staging `FEATURE_BRIEF` PS-3 / AC3.2 / AC4.2 / AC6). The agent runs every
*agent-verifiable* check (see [TEST_PLAN.md](../../features/platform-staging/TEST_PLAN.md)); the
checks below that say **[sign-off]** are yours to judge and record.

**Before you start:**
- The deploy is green per [deploy-runbook.md](deploy-runbook.md) (incl. email wired per
  [email-provider-setup.md](email-provider-setup.md), and an admin bootstrapped).
- You have the staging base URL `https://<host>`, a desktop browser, and a phone (or the
  browser devtools device emulator at a phone width, e.g. 390×844).
- Have a throwaway real email inbox ready (magic-link sign-in needs a real inbox).

Record each step as **PASS / FAIL / N/A** with a note. Log every defect in the register at the
end (AC6.1 / M7) — a defect is *fixed* (commit) or *logged* (owner + disposition), never
silently dropped.

> Tip: do each role on **desktop first**, then repeat the public-facing parts on **mobile**.
> The mobile pass is the load-bearing one (M4) — the app page and widget are the wedge's public
> face.

---

## Role 1 — Developer (web)

The public face you'll show your audience. Sign in, list an app, make it public, embed.

1. **Sign in (magic link).** Go to `https://<host>/auth/register` (or `/auth/signin`), enter a
   real email, submit. → **the email actually arrives** at the inbox (not the console). Click
   the link; you're signed in. **[sign-off — AC3.1: email arrived via the real transport]**
2. **Become a developer.** Profile → "Become a developer".
3. **Submit an app.** Catalog → submit: name, URL, description, ≥1 tag, ≥1 screenshot. Submit.
4. **(Admin step needed before it's public — see Role 3; ACCEPT it, then return.)**
5. **Edit the public app page.** Confirm the app page `/apps/<id>/` shows your content,
   screenshots render, tags show, the "try it" link works.
6. **Post an update.** Updates → post a changelog entry; confirm it shows on the channel.
7. **Embed the widget.** Grab the widget embed for your app `/widget/<id>/`; open it; click
   through to the app page. (The agent confirms the conversion funnel records — AC3.3.)
8. **Read your dashboard.** `/dashboard/` → your app's reception: reach / engagement / ratings /
   the widget conversion funnel. Confirm it loads and reflects the activity above.

   **Each step completes end-to-end?** PASS/FAIL: __________

## Role 1 — Developer (mobile)

Repeat the **public-facing** surfaces on a phone-sized viewport:

- The **app page** `/apps/<id>/` — screenshots, description, follow/try controls.
- The **embeddable widget** `/widget/<id>/`.

> **[sign-off — AC3.2]** Both render **without layout breakage** and read as **credible, not
> raw**, on mobile: PASS / FAIL — note: __________________________________

---

## Role 2 — Audience member (web)

Arriving from an app page or widget; the bring-your-own-audience capture path.

1. **Arrive** on an app page `/apps/<id>/` (signed out).
2. **Register** a new account (magic link), as a plain user.
3. **Follow** the app from its page.
4. **Set interests.** `/interests/` → pick a few; save.
5. **Browse / search.** `/discover/` → browse newest, run a keyword search, filter by a tag.
6. **Check the feed.** `/subscriptions/feed` → the followed app (and any updates) appears.

   **Each step completes end-to-end (desktop)?** PASS/FAIL: __________

## Role 2 — Audience member (mobile)

Repeat **registration** and **browse/search** on a phone-sized viewport.

> **[sign-off — AC4.2]** Registration and browse/search are **usable without layout breakage**
> on mobile: PASS / FAIL — note: __________________________________

---

## Role 3 — Admin / operator

Run the platform, not just demo it.

1. **Review + ACCEPT a submission.** `/django-admin/` (or the review surface) → take the
   developer's PENDING app and **ACCEPT** it. → it becomes visible on `/discover/` per the D-6
   gate. **(AC5.1 — agent re-verifies.)**
2. **Confirm email is sending.** You already saw the magic-link arrive (Role 1/2). Optionally
   hit `GET /health` (operator deep probe) → `email: true`.
3. **Observe health + monitoring.** Logs stream in the Render dashboard; `GET /health/live`
   returns `{"status":"ok"}`; if `SENTRY_DSN` is set, force a test error and confirm it lands in
   Sentry. (AC5.2)

   **Operations path works?** PASS/FAIL: __________

---

## Defect register (AC6.1 / M7)

Every defect found above, with disposition. Zero unresolved **blockers** is required for a *go*.

| # | Where (role/surface) | Defect | Severity | Disposition (fixed `commit` / logged `owner`) |
|---|---|---|---|---|
|   |   |   |   |   |

---

## Verdict 1 — Go / No-Go for live recruitment (AC6.1)

> **Decision:** ☐ GO  ☐ NO-GO
>
> All three role journeys attempted: ☐ yes. Blocking defects remaining: ____.
>
> Rationale: ______________________________________________________________

## Verdict 2 — Frontend evidence (AC6.2)

> **Verdict:** ☐ Templates sufficient (no SPA needed now)  ☐ Specific surface(s) need more
>
> If "need more", name the surface(s) and the concrete evidence (what breaks / what's
> insufficient), feeding the D-11 evidence-gated SPA decision (a D-4-revisit ADR, **not** a
> silent rewrite):
> ________________________________________________________________________
