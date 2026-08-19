# Deploying SS Tuitions

## Current state (2026-08-19)

**The website IS deployed and live: <https://ss-tuitons.vercel.app>**
Homepage, reviews, contact and WhatsApp all work publicly on any device.

**The backend is NOT deployed.** It runs locally only, so login, dashboards,
fees, messaging and the AI tutor work on the owner's machine but not on the
public site. Everything needed to deploy it is ready — only a host is missing.

### Hosts already tried, and why they failed

| Host | Outcome |
|---|---|
| **Koyeb** | Signup stalled — the company is merging with Mistral |
| **Hugging Face Spaces** | Pushed and configured successfully, but the account has `limit=0` for free `cpu-basic`. Error: `Quota exceeded for flavor cpu-basic (requested=1): current=0, limit=0`. Adding a payment method to HF may raise the quota. |
| **Render** | Not attempted — asks for a card. The Free tier is genuinely $0/month and never billed; the card is identity verification only. **This remains the recommended option**, and its Singapore region is closest to the Mumbai database. |

### What is already prepared

- `Dockerfile` (repository root) — runs migrations at start-up, non-root user, healthcheck.
  It sits at the root because that is where Render's default Dockerfile Path looks.
- `backend/README.md` — Hugging Face front matter (`sdk: docker`, `app_port: 8000`)
- `backend/scripts/configure_hf_space.py` — pushes all 25 variables + 6 secrets
  to a HF Space in one command, reading them from `.env`
- `backend/scripts/restart_hf_space.py` — restarts a Space via API
- Production config guard refuses to boot with unsafe cross-site cookie settings

### To finish deployment later

1. Pick a host that will actually run a container (Render is the shortest path).
2. Root directory `backend`, runtime **Docker**, port **8000**.
3. Set the environment variables — the list and the production overrides are in
   `backend/scripts/configure_hf_space.py` (`WANTED` and `PRODUCTION_OVERRIDES`).
4. On Vercel, set `NEXT_PUBLIC_API_BASE_URL` to `https://<backend-url>/api/v1`.
5. On the backend, set `FRONTEND_BASE_URL` and `CORS_ALLOWED_ORIGINS` to
   `https://ss-tuitons.vercel.app`, plus `COOKIE_SAMESITE=none` and
   `COOKIE_SECURE=true` — the app refuses to start otherwise, deliberately.

---


Goal: a real web address parents can open on their phones, instead of
`localhost` on one computer.

**Cost: ₹0 to start.** Vercel, Render and Supabase all have free tiers that
cover a business of this size.

---

## What goes where

| Piece | Host | Free tier |
|---|---|---|
| Website (Next.js) | **Vercel** | Yes, generous |
| API (FastAPI) | **Render** | Yes — sleeps after 15 min idle |
| Database | **Supabase** | Already running, Mumbai |
| Code | **GitHub** | Yes, private repo |

> **The Render free tier sleeps.** After 15 minutes with no traffic the first
> request takes ~50 seconds to wake it. Fine while testing; not fine when a
> parent taps *Join class* two minutes before a lesson. Render's paid tier is
> about ₹600/month and removes it. Start free, upgrade before real students
> depend on it.

---

## Step 1 — Put the code on GitHub

The repository is local only. It needs a remote so Vercel and Render can build
from it.

```bash
cd C:\dev\ss-tuitions && git remote -v
```

If that prints nothing, create a **private** repository on github.com, then:

```bash
cd C:\dev\ss-tuitions && git remote add origin https://github.com/YOUR-USERNAME/ss-tuitions.git && git push -u origin main
```

**Make it private.** The repository contains your business logic and structure.
`.env` is gitignored, so no passwords or keys are pushed — that is worth
verifying once with `git log -p | Select-String "GEMINI_API_KEY="` returning
nothing.

---

## Step 2 — Deploy the API on Render

1. render.com → sign in with GitHub → **New → Web Service**
2. Pick the `ss-tuitions` repository
3. Settings:
   - **Root directory:** `backend`
   - **Runtime:** Docker
   - **Region:** Singapore (closest to Mumbai)
4. Add environment variables — copy from your local `.env`, with these
   **changed**:

```
APP_ENV=production
COOKIE_SECURE=true
COOKIE_SAMESITE=none
FORCE_HTTPS=true
BACKEND_BASE_URL=https://YOUR-SERVICE.onrender.com
FRONTEND_BASE_URL=https://YOUR-SITE.vercel.app
CORS_ALLOWED_ORIGINS=https://YOUR-SITE.vercel.app
```

Everything else — `DATABASE_URL`, `JWT_SECRET`, `MESSAGE_ENCRYPTION_KEY`,
`GEMINI_API_KEY`, the `PAYMENT_*` values, the email settings — copies across
unchanged.

> **`COOKIE_SAMESITE=none` is not optional.** Vercel and Render are different
> domains, so a `lax` cookie is never sent back: sign-in returns success and
> then silently fails. The app refuses to boot in production with this wrong,
> rather than letting you discover it from a confused parent.

Migrations run automatically on deploy.

---

## Step 3 — Deploy the website on Vercel

1. vercel.com → **Add New → Project** → same repository
2. **Root directory:** `frontend`
3. Environment variable:

```
NEXT_PUBLIC_API_BASE_URL=https://YOUR-SERVICE.onrender.com/api/v1
```

4. Deploy

Then go back to Render and correct `FRONTEND_BASE_URL` and
`CORS_ALLOWED_ORIGINS` to the real Vercel URL.

---

## Step 4 — Check it before telling anyone

Open `https://YOUR-SERVICE.onrender.com/api/v1/ready` — expect:

```json
{"ready": true, "database": "connected", "tables_found": 49}
```

Then on the live site:

- [ ] Homepage loads, WhatsApp button works
- [ ] Sign in as owner **and stay signed in after a refresh** — this is the
      cookie check
- [ ] `/admin` shows your real counts
- [ ] Sign in as a parent on a **phone**
- [ ] Send a message; it arrives
- [ ] Open the AI tutor and ask a question

The refresh test matters most. If it bounces you to login, `COOKIE_SAMESITE`
is wrong.

---

## Step 5 — Custom domain (optional)

A domain such as `sstuitions.in` costs roughly ₹700–1,200/year.

Pointing the site at `sstuitions.in` and the API at `api.sstuitions.in` also
makes them same-site, so `COOKIE_SAMESITE` can go back to `lax` — one less
thing to get wrong.

---

## Before real student data goes in

**Backups.** The Supabase free tier has none. Once the database holds real
marks, attendance and fee records, losing it means losing your business
records. Either Supabase Pro (~₹2,100/month, daily backups plus 7-day
point-in-time recovery) or a scheduled `pg_dump` to storage you control.

**Rotate the keys that have been shared in chat**, if any: `GEMINI_API_KEY`
and the database password.

**Consent wording.** Students are minors and the AI tutor sends their questions
to Google. `docs/PRIVACY_MODEL.md` has the exact wording to show parents.
