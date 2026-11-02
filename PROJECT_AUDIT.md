# Al-Tariq Project Audit

## Architecture

- **Backend:** FastAPI in `backend/main.py`, with NASA APOD/DONKI access in
  `backend/nasa_client.py`, Pydantic response models, optional APScheduler
  bulletins, and OpenRouter text/vision providers.
- **Canonical frontend:** Next.js 14 + React 18 + TypeScript in `frontend/`.
  It is Arabic-first, RTL, responsive, and calls the backend through the typed
  client in `frontend/lib/api.ts`.
- **Legacy frontend:** `al-tariq-frontend/` is a separate static prototype with
  additional exploratory pages. It remains in the repository for reference but
  is not the supported application entry point.
- **Persistence:** the optional bulletin scheduler writes a local JSON store;
  favorites are browser-local.

## Existing functionality

The backend exposes health, daily APOD story generation, bulletin status,
APOD analysis, image analysis, AI chat, space weather, and stories archive
endpoints. The Next.js app provides dashboard, image interpreter, chat, stories,
and favorites routes, with loading/error/empty states and RTL typography.

## Problems found and addressed

1. The repository had no single Replit startup path; `.replit` and
   `scripts/start-replit.sh` now start both services.
2. A browser deployed from Replit could not safely rely on
   `localhost:8000`; Next.js now proxies `/backend-api/*` to the private
   FastAPI port, while `NEXT_PUBLIC_API_URL` remains available for split
   deployments.
3. FastAPI CORS was open to every origin. It now defaults to local development
   origins and is configurable with `CORS_ALLOW_ORIGINS`.
4. Release instructions and a secret-safe environment template were incomplete;
   the companion Replit and development reports document the supported path.

## Important decisions

The existing Next.js frontend was selected rather than rewriting the working
static prototype. No API contracts or provider abstractions were removed.
Missing OpenRouter credentials still allow the backend to start; AI routes
return an explicit configuration error instead of fabricating results.
