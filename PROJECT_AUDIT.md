# Al-Tariq Project Audit

## Architecture

- **Backend:** FastAPI in `backend/main.py`, with NASA APOD/DONKI access in
  `backend/nasa_client.py`, Pydantic response models, optional APScheduler
  bulletins, and OpenRouter text/vision providers.
- **Canonical frontend:** `al-tariq-frontend/`, a zero-build Node-served
  bilingual static application with shared CSS/JS, persisted AR/EN switching,
  RTL/LTR direction, and the full exploratory page set.
- **Secondary frontend:** Next.js 14 + React 18 + TypeScript in `frontend/`.
  It remains preserved and testable, but is not started by the default Replit
  command.
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
   `localhost:8000`; the canonical Node server now streams `/api/*` and
   `/health` to the private FastAPI port.
3. FastAPI CORS was open to every origin. It now defaults to local development
   origins and is configurable with `CORS_ALLOW_ORIGINS`.
4. Release instructions and a secret-safe environment template were incomplete;
   the companion Replit and development reports document the supported path.

## Important decisions

The existing static frontend was selected rather than rewriting it or creating
a third frontend. No API contracts or provider abstractions were removed.
Missing OpenRouter credentials still allow the backend to start; AI routes
return an explicit configuration error instead of fabricating results.
