# Email provider setup — Resend (SMTP)

This guide wires a real transactional-email provider so magic-link sign-in actually
delivers (platform-staging `FEATURE_BRIEF` PS-2, `DESIGN` §4.4). Until this is done, the
app runs the **console** backend (it prints links to the log), which is fine for local
dev but means **no email arrives** — magic-link sign-in (AC3.1 / M5) cannot be verified.

The app needs **no code change**: the email transport is selected entirely by env vars
(`apps/core/email.py` + `config/settings.py`). This is pure configuration.

## Why Resend

- Free tier (100 emails/day, 3 000/mo) comfortably covers staging magic-links.
- Clean SMTP interface, modern low-friction domain verification.
- **Alternative — Postmark**: pick it instead if inbox placement becomes the
  bottleneck (deliverability-premium; 100/mo free → ~$15/mo, inside the PS-1 budget).
  The steps below are identical; only the host/credentials differ.

## Steps

1. **Create an account** at <https://resend.com> and sign in.

2. **Add and verify a sending domain.** In the dashboard go to **Domains → Add Domain**
   and enter the domain you will send *from* (e.g. `app-discovery.example`). Resend shows
   DNS records to add at your domain registrar:
   - an **SPF** record (TXT),
   - **DKIM** records (CNAME/TXT),
   - (optional but recommended) a **DMARC** TXT record.
   Add them, then click **Verify**. Verification can take a few minutes to a few hours
   while DNS propagates. *You cannot send from an unverified domain.*

   > No domain yet? Resend allows sending from its shared `onboarding@resend.dev`
   > sandbox address to your own verified email for a first smoke test, but a verified
   > domain is required before the staging walkthrough.

3. **Obtain SMTP credentials.** In **API Keys / SMTP**, Resend exposes the SMTP settings:
   - host: `smtp.resend.com`
   - port: `587` (STARTTLS) — use TLS
   - username: `resend`
   - password: your **API key** (create one with *Sending access*)

4. **Set the environment variables** (in the Render dashboard for the web service — they
   are declared as `sync: false` secrets in `render.yaml`, so set their values there;
   for a local SMTP test put them in `.env`):

   ```
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.resend.com
   EMAIL_PORT=587
   EMAIL_HOST_USER=resend
   EMAIL_HOST_PASSWORD=<your Resend API key>
   EMAIL_USE_TLS=true
   DEFAULT_FROM_EMAIL=no-reply@your-verified-domain.example
   ```

   `DEFAULT_FROM_EMAIL` **must** be at the verified domain or sends will be rejected.

5. **Send a test.** With the env set, trigger a real send and confirm it lands in an inbox:

   ```bash
   python manage.py shell -c "from django.core.mail import send_mail; \
     send_mail('App Discovery test', 'It works.', None, ['you@example.com'])"
   ```

   Then run the actual sign-in flow (request a magic link for a real address) and confirm
   the email arrives. The operator deep probe `GET /health` reports `email: true` when the
   SMTP connection opens — note that `/health/live` deliberately does **not** check email
   (so a provider blip never marks the service unhealthy; `DESIGN` §4.6).

## Failure behaviour (by design)

Email failures are **loud, never silent**: `DefaultEmailSender` sends with
`fail_silently=False`, so a bad credential or a down provider raises and the registration
flow surfaces the error rather than silently dropping the link (`DESIGN` §9). If sends
fail, re-check the API key, the verified `DEFAULT_FROM_EMAIL` domain, and `EMAIL_USE_TLS`.
