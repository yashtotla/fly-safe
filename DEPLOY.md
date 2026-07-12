# Deploying fly-safe

Backend → **Fly.io**, frontend → **Vercel**. They reference each other's URLs, so the
order matters: deploy the backend first, point the frontend at it, then tell the
backend to trust the frontend's origin (CORS).

## 1. Backend (Fly.io)

```bash
cd backend
fly auth login
fly launch --no-deploy            # or keep the provided fly.toml; pick a unique app name + region
fly volumes create flysafe_data --size 1   # persistent SQLite cache + change-log
fly secrets set AERODATABOX_API_KEY=<your key>
fly secrets set GITHUB_TOKEN=<repo-scoped token>   # optional: enables failure-issue alerts
fly deploy
```

Note the app URL (e.g. `https://fly-safe-api.fly.dev`). `POLL_ENABLED=true` is already
set in `fly.toml`, so it begins polling on its cadence (flight status ~1×/day).

## 2. Frontend (Vercel)

```bash
cd frontend
vercel                             # link the project; set "Root Directory" = frontend
```

In the Vercel project settings add an environment variable:

```
VITE_API_URL = https://fly-safe-api.fly.dev
```

Then redeploy (`vercel --prod`). Note the frontend URL (e.g. `https://fly-safe.vercel.app`).

## 3. Close the CORS loop

Tell the backend to accept the frontend origin:

```bash
cd backend
fly secrets set CORS_ORIGINS='["https://fly-safe.vercel.app"]'
```

(Fly restarts the app on secret change.) Done — open the Vercel URL.

## Cost

Year one is ~free: Fly ~$3–6/mo (covered by GitHub Student / Azure credits if used),
Vercel Hobby free (non-commercial), AeroDataBox free tier (~100 flight calls/month;
the poller is budgeted to ~1×/day). See `NOTES.md` §5.

## CI

`.github/workflows/ci.yml` lints + tests the backend and builds the frontend on every
push/PR. Deploy is manual (above); wire up `flyctl deploy` / Vercel Git integration
later if you want push-to-deploy.
