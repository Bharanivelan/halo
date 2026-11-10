# Building the Halo web app in Lovable

The Halo UI is built in [Lovable](https://lovable.dev) as its own repo (`halo-web`). It talks to this API (`halo-api`)
over HTTPS with a bearer token. Lovable owns the look; the API owns all data and logic (D-34, D-35, D-36).

## What's in this folder

| File | Use |
|---|---|
| [00-project-knowledge.md](00-project-knowledge.md) | Paste into **Lovable → Project settings → Knowledge**. Brand, colours, fonts, rules, routes, vocabulary. Lovable applies it to every prompt |
| [01-prompts.md](01-prompts.md) | The prompt sequence (10 prompts), one screen at a time |
| [kit/src/lib/halo-api.ts](kit/src/lib/halo-api.ts) | Ready-made API client: bearer auth, server URL setting, typed calls for every endpoint, CSV download |
| [kit/src/lib/halo-types.ts](kit/src/lib/halo-types.ts) | The API's TypeScript contract (generated from the backend) |
| [openapi.json](openapi.json) | Full OpenAPI spec (also live at `<API_URL>/api/v1/docs`) |

## Step by step

1. **Create the project.** In Lovable, start a new project and paste **Prompt 1** from `01-prompts.md`.
2. **Add the knowledge.** Project settings → Knowledge → paste `00-project-knowledge.md`.
3. **Connect GitHub.** Lovable → GitHub → Connect → create repo `halo-web` (private).
4. **Add the API kit.** Push `kit/src/lib/*` into `halo-web/src/lib/` (Claude can do this once the repo exists),
   or paste each file into Lovable: *"Create src/lib/halo-api.ts exactly as given: …"*.
5. **Expose the API.** Start the stack (`scripts/dev.ps1`), then `scripts/tunnel.ps1`. Copy the public URL.
6. **Send Prompt 2**, then sign in from the Lovable preview: *Connection settings → Server URL →* paste the tunnel URL
   → *Test connection* → sign in.
7. Continue with Prompts 3–10, checking each in the preview.
8. For a fixed demo URL, set `DEFAULT_API_URL` in `src/lib/halo-api.ts` to your ngrok static domain (or deployed API).

## How auth works for this app

- `halo.login()` sends `POST /api/v1/auth/login` with header `X-Auth-Mode: token`; the API returns `access_token`
  (no cookie). Every later call sends `Authorization: Bearer <token>`. No CSRF header is needed for bearer requests.
- The token is a normal server-side session (same expiry and revocation as cookie sessions); `halo.logout()` revokes it.
- It's stored in `localStorage`, so the app must not render untrusted HTML (XSS would expose it). Acceptable for the
  demo; revisit before real customers (D-36).
- CORS allows `localhost:5173`, `localhost:8080` and `*.lovable.app`, `*.lovableproject.com`, `*.lovable.dev`
  (`CORS_ORIGIN_REGEX` in `.env` to change). Add a custom domain to `CORS_ORIGINS` when you publish one.

## Keeping the contract in sync

When the API changes, regenerate and re-push the kit:
`curl http://localhost:8000/api/v1/openapi.json > docs/lovable/openapi.json`, update `kit/src/lib/halo-types.ts`
from the backend schemas, and push to `halo-web/src/lib/`.
