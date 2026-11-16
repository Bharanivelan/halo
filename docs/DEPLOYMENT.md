# Deploying Halo: Supabase (database) + Railway (API and worker)

This puts Halo online with a permanent web address, so it works when your own computer is off (D-50).

```
 Web app (Lovable, published)  ──▶  API on Railway (https://<name>.up.railway.app)  ──▶  Postgres on Supabase
                                     worker on Railway (runs the agent)              ──┘   (session pooler, IPv4)
```

Approximate cost: Supabase free tier; Railway about $5 a month for the API and worker.

## 1. Database on Supabase

1. Create a project at <https://supabase.com/dashboard>. Choose a strong **database password** and keep it.
   Pick the region closest to where Railway will run (e.g. *East US (North Virginia)*).
2. **Switch off the Data API**: *Project Settings → Data API* → disable. Halo has its own API and logins; Supabase's
   automatic API must not expose Halo's tables. (The setup script below also revokes its access.)
3. Copy the **Session pooler** connection string: *Connect* (top bar) → *Session pooler*. It looks like
   `postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`.
   Use the session pooler, not the direct connection (direct is IPv6-only on the free tier) and not the transaction
   pooler (port 6543).
4. Choose a second strong password for Halo's restricted database user `inhabitr_app`, then run once (needs `psql`;
   with Docker: `docker run --rm -i postgres:16 psql ...`):

   ```bash
   psql "postgresql://postgres.<ref>:<db-password>@aws-0-<region>.pooler.supabase.com:5432/postgres" \
        -v app_password='<app-password>' -f scripts/cloud/supabase_init.sql
   ```

   It enables PostGIS, citext and pg_trgm, creates `inhabitr_app` (row-level security applies to it) and removes
   Supabase's public roles from Halo's tables.

The tables themselves are created by the API on its first start (`alembic upgrade head`).

**Connection strings Halo uses** (note the `+psycopg` and the user name `<role>.<project-ref>`):

| Variable | Value |
|---|---|
| `DATABASE_OWNER_URL` | `postgresql+psycopg://postgres.<ref>:<db-password>@aws-0-<region>.pooler.supabase.com:5432/postgres` |
| `DATABASE_URL` | `postgresql+psycopg://inhabitr_app.<ref>:<app-password>@aws-0-<region>.pooler.supabase.com:5432/postgres` |

URL-encode passwords that contain `@ : / ? # %`.

### Moving existing data (optional)

From the machine that has your local database, after the API has created the tables once:

```bash
docker exec inhabitragent-db-1 pg_dump -U inhabitr_owner -d inhabitr --data-only --schema=public \
  --exclude-table=public.alembic_version --exclude-table=public.spatial_ref_sys --no-owner --no-privileges > halo_data.sql
psql "<DATABASE_OWNER_URL without +psycopg>" -v ON_ERROR_STOP=1 --single-transaction \
  -c "SET session_replication_role = replica" -f halo_data.sql
```

`session_replication_role = replica` lets the copy load in any order (some tables reference each other). Delete
`halo_data.sql` afterwards: it contains your data and login hashes.

## 2. API and worker on Railway

1. Sign in at <https://railway.com> with GitHub. *New Project → Deploy from GitHub repo →* `halo`.
2. In the service that appears, open *Settings*:
   - **Root Directory**: `backend` (Railway then builds `backend/Dockerfile`).
   - **Name**: `api`.
   - *Networking → Generate Domain* (port 8080 is fine; Halo listens on `$PORT`).
   - *Deploy → Healthcheck Path*: `/healthz`.
3. *Variables → Raw Editor*, paste:

   ```ini
   APP_ENV=prod
   DATABASE_OWNER_URL=...
   DATABASE_URL=...
   DB_POOL_SIZE=4
   DB_MAX_OVERFLOW=2
   SECRET_KEY=<a long random string>
   COOKIE_SECURE=true
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=...
   LLM_MAX_RPM=8
   HTTP_USER_AGENT=HaloBot/0.1 (B2B account research; respects robots.txt)
   ```

   Any provider from the README's *Choose an AI provider* works here (e.g. Bedrock with AWS keys).
4. Add the worker: *+ Create → GitHub Repo →* `halo` again, then *Settings*:
   - **Root Directory**: `backend`, **Name**: `worker`.
   - *Deploy → Custom Start Command*: `python -m app.worker`.
   - No domain, no healthcheck.
   - *Variables*: the same as the API (Railway: *Shared Variables*, or paste the same block).
5. Deploy both. The API applies migrations on start; its logs end with `Uvicorn running on http://0.0.0.0:...`.
   Check `https://<api-domain>/readyz` returns `{"ok": true, ...}`.

Each push to `main` redeploys both services.

## 3. Point the web app at it

- Lovable app: set `DEFAULT_API_URL` in `web/src/lib/halo-api.ts` (or `VITE_HALO_API_URL` at build time) to the
  Railway API domain, then **Publish** in Lovable. Users can also change it under *Connection settings* on the sign-in page.
- CORS already allows Lovable domains and localhost; for another web domain add it to `CORS_ORIGINS`.

## 4. First login on an empty database

If you didn't move data, create the workspace and admin from your machine against the cloud database:

```bash
cd backend
DATABASE_URL="<DATABASE_URL>" DATABASE_OWNER_URL="<DATABASE_OWNER_URL>" \
  .venv/Scripts/python -m app.cli bootstrap --workspace "Halo" --email you@company.com --name "Your Name"
```

## Notes

- **Supabase free projects pause** after about a week without activity; resume from the dashboard.
- **Connections**: the session pooler allows about 15 connections per database user on the free tier. API and
  worker each use at most `DB_POOL_SIZE + DB_MAX_OVERFLOW` (4 + 2). Keep the sum under the limit if you scale out.
- **Secrets** live only in Railway variables and your local `.env*` files (git-ignored), never in the repository.
