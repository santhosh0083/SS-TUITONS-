---
title: SS Tuitions API
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# SS Tuitions API

FastAPI backend for the SS Tuitions platform. Deployed as a Docker Space.

- Health check: `/api/v1/health`
- Readiness (DB + migration state): `/api/v1/ready`
- API docs: `/docs`

Secrets (database URL, JWT secret, encryption key, Gemini key, SMTP
password) are provided at runtime via the Space's secrets, never committed.
The frontend runs separately on Vercel and calls this API.
