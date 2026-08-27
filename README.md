# النجم الطارق — Al-Tariq

### AI-Powered Arabic Space Interpreter

> **MVP / Prototype — actively evolving**

---

## Project Overview

Al-Tariq is an Arabic-focused, AI-powered space exploration and interpretation platform. It connects NASA's public APIs with a large language model gateway (OpenRouter) to make complex astronomy and space science content understandable and accessible to Arabic-speaking audiences.

The platform fetches real daily space data from NASA, generates structured Arabic scientific narratives, and provides a conversational AI interface for exploring space topics — all within an architecture that keeps API credentials exclusively server-side.

---

## The Problem

Astronomy content is largely inaccessible to Arabic-speaking non-specialists:

- **Almost all primary sources are in English.** NASA publications, APOD captions, and space-weather bulletins use specialised scientific vocabulary that is rarely translated into Arabic at a level appropriate for general audiences.
- **Space imagery lacks contextual explanation.** When someone encounters an image of a nebula, galaxy, or solar event, there is no easy way to ask *"what is this?"* in Arabic and receive a scientifically grounded answer.
- **No conversational AI tuned for Arabic space education exists.** General-purpose chatbots are not focused on Arabic space literacy or on discussing specific images.
- **Space data is scattered.** Daily astronomy pictures, space-weather events, and archived stories are hosted in separate places with no unified Arabic-language interface.

---

## Our Solution

Al-Tariq builds a unified platform that combines NASA's public APIs, an OpenRouter-powered AI layer, and two frontend implementations into one coherent experience.

The implemented system provides:

- **Daily NASA APOD content** — fetched live and accompanied by a full AI-generated Arabic scientific interpretation.
- **NASA DONKI space-weather data** — Coronal Mass Ejection events from NASA's real-time space-weather service, integrated into the daily bulletin.
- **AI-generated Arabic scientific stories** — produced by a large language model with prompt engineering enforcing Arabic output, scientific accuracy, and structured JSON validation.
- **Conversational space AI chat** — multi-turn Arabic conversation about astronomy topics, with optional image context.
- **Image upload and Vision AI analysis** — users upload any space image; the backend sends it to a multimodal vision model and returns a structured Arabic interpretation (title, summary, observations, scientific explanation, confidence level, and an answer to the user's specific question).
- **NASA stories archive** — paginated browsing of past APOD entries.
- **A fully RTL Arabic interface** in the Next.js frontend, and a modern English LTR space-themed interface in the static al-tariq-frontend.

All AI and NASA API calls are made server-side. No API keys are ever exposed to the browser.

---

## Key Features

All features listed below are implemented and present in the repository.

| Feature | Notes |
|---|---|
| NASA APOD daily content | Live fetch from `https://api.nasa.gov/planetary/apod` |
| NASA DONKI space weather | CME events from `https://api.nasa.gov/DONKI/CME` |
| AI Arabic scientific story | Structured JSON story generated via OpenRouter |
| AI astronomy chat | Multi-turn conversational AI (`POST /api/chat`) |
| Image upload | User selects a local image file |
| Vision AI analysis | Multimodal model; returns structured Arabic result |
| Question about uploaded image | Optional Arabic question submitted with the image |
| Stories archive | Paginated APOD history (`GET /api/stories`) |
| Favorites | LocalStorage-based favorites across pages |
| RTL Arabic interface | `<html lang="ar" dir="rtl">` in the Next.js frontend |
| Daily bulletin scheduler | Optional APScheduler job for automated daily stories |
| Model fallback logic | Automatic retry on rate-limit / service-unavailable errors |

### Application Routes (Next.js frontend)

| Route | Page |
|---|---|
| `/` | Home dashboard (APOD story + space weather) |
| `/interpreter` | Image upload and Vision AI analysis |
| `/chat` | AI space chat |
| `/stories` | NASA stories archive |
| `/favorites` | Saved favorites |

### Application Pages (al-tariq-frontend static)

| Page | Description |
|---|---|
| `index.html` | Home / Morning Bulletin |
| `interpreter.html` | Vision AI image upload |
| `chat.html` | AI space conversation |
| `stories.html` | NASA/APOD story archive with search |
| `favorites.html` | Local favorites |
| `exoplanets.html` | Exoplanet catalog explorer |
| `weather.html` | Solar and geomagnetic monitor |
| `pulsar-lab.html` | Pulsar physics workbench |
| `calendar.html` | Astronomy events calendar |
| `observatory.html` | Observatory view |
| `mission-timeline.html` | Mission timeline |
| `settings.html` | Settings / API proxy placeholder |

---

## System Architecture

```
User
 ↓
Frontend (Next.js or al-tariq-frontend static)
 ↓
FastAPI Backend (Python) — port 8000
 ┌────────────────────────┬────────────────────────┐
 │   NASA APIs            │   OpenRouter AI         │
 │   APOD + DONKI         │   Text + Vision models  │
 └────────────────────────┴────────────────────────┘
 ↓
Pydantic-validated response envelope
 ↓
Frontend
```

### Text AI Path

1. The frontend calls `GET /api/daily-news` or `POST /api/analyze`.
2. `NASAClient` fetches the APOD data and, optionally, DONKI CME events.
3. `prompts.py` builds a structured system + user prompt enforcing Arabic output and a specific JSON schema.
4. `OpenRouterProvider.generate_structured_response()` calls the OpenRouter API with the configured primary model; if the primary model returns a rate-limit or unavailability error, the configured fallback model is tried automatically.
5. The raw response is parsed (including stripping markdown fences if present).
6. `SpaceStory` (Pydantic model) validates the structure; a `model_validator` also corrects the `language` field if the AI returns English content while claiming `"language": "ar"`.
7. The validated `SpaceStory` is serialised and returned to the frontend.

### Vision AI Path

```
User selects image
 → multipart/form-data (image + optional Arabic question)
 → POST /api/analyze-image
 → MIME type validation (JPEG / PNG / WEBP only)
 → File size validation (max 5 MB)
 → base64 encoding (no temp file written)
 → vision system prompt + user prompt constructed
 → OpenRouterProvider.analyze_image() (multimodal request)
 → Configured vision model (primary → fallback on error)
 → raw JSON response parsed
 → ImageAnalysisResult (Pydantic) validated
 → Arabic structured result returned to frontend
```

### NASA Data Path

- **APOD** — `NASAClient.get_apod(apod_date?)` calls `https://api.nasa.gov/planetary/apod`. The response is normalised into a `NASAAPODData` Pydantic model. APOD is required; the pipeline returns an error if it is unavailable.
- **DONKI** — `NASAClient.get_donki_cme()` calls `https://api.nasa.gov/DONKI/CME`. DONKI is non-fatal; if it is unavailable the story is still generated using APOD data only.

Both NASA calls are cached with a TTL to avoid redundant requests.

### Validation and Safety

- All AI output is validated via Pydantic models (`SpaceStory`, `ImageAnalysisResult`).
- A `model_validator` on `SpaceStory` corrects the `language` field if the AI returns English content.
- `field_validator` on `confidence` normalises values to `high | medium | low`.
- Image MIME type is checked against an allowlist.
- Image size is enforced at 5 MB maximum.
- Chat messages are truncated server-side at 800 characters; history is capped at 20 turns.
- API keys are never exposed to the frontend.
- All error responses use a `{"success": false, "error": {"code": "...", "message": "..."}}` envelope; stack traces are never surfaced.
- CORS is currently open (`allow_origins=["*"]`) for development convenience; this should be tightened before production deployment.

---

## Technology Stack

### Backend

| Technology | Purpose |
|---|---|
| Python 3.11+ | Primary backend language |
| FastAPI | REST API framework with async support |
| Pydantic v2 | Data validation and serialisation |
| httpx | Async HTTP client (NASA API calls) |
| APScheduler | Optional daily bulletin scheduler |
| python-multipart | Multipart form handling for image upload |
| python-dotenv | Environment variable loading |
| uvicorn | ASGI server |

### Next.js Frontend (`frontend/`)

| Technology | Purpose |
|---|---|
| Next.js 14 | React framework, routing, image optimisation |
| React 18 | UI component library |
| TypeScript 5 | Static typing |
| Tailwind CSS 3 | Utility-first styling and responsive layout |

### Al-Tariq Static Frontend (`al-tariq-frontend/`)

| Technology | Purpose |
|---|---|
| Vanilla HTML / CSS / JavaScript | Zero-dependency static pages |
| Node.js (zero-dependency server) | Local static file server (`server.js`) |

### AI

| Technology | Purpose |
|---|---|
| OpenRouter | AI gateway providing access to multiple models |
| Configurable text model | Arabic story generation (default: `google/gemini-2.0-flash-exp:free` per `.env.example`) |
| Configurable vision model | Multimodal image analysis |
| Configurable fallback models | Automatic retry on primary model failure |

### Data

| Source | Purpose |
|---|---|
| NASA APOD API | Daily astronomy image and explanation |
| NASA DONKI API | Space-weather CME event data |

### Testing

| Tool | Purpose |
|---|---|
| pytest + pytest-asyncio | Backend unit and integration tests |
| Jest | Frontend JavaScript test runner |
| React Testing Library | Frontend component tests |

---

## Data and AI Integrations

| Integration | Type | Notes |
|---|---|---|
| NASA APOD | REST API (public) | Free; `DEMO_KEY` available for light testing |
| NASA DONKI | REST API (public) | CME space-weather events |
| OpenRouter | AI gateway | Requires an API key; free tier available |
| Primary text model | Configurable via `OPENROUTER_MODEL` | See `.env.example` for recommended defaults |
| Vision model | Configurable via `OPENROUTER_VISION_MODEL` | Must support OpenAI vision `image_url` format |
| Fallback models | Configurable via `OPENROUTER_FALLBACK_MODEL` / `OPENROUTER_VISION_FALLBACK_MODEL` | Activated automatically on rate-limit errors |

---

## Repository Structure

```
.                                  # Project root
├── backend/                       # Python FastAPI application
│   ├── main.py                    # FastAPI app — all endpoints, lifecycle
│   ├── config.py                  # Environment-based configuration (dataclasses)
│   ├── models.py                  # All Pydantic models (NASA, AI output, API envelopes)
│   ├── nasa_client.py             # Async HTTP client for APOD and DONKI (with TTL cache)
│   ├── ai_provider.py             # Abstract AIProvider interface
│   ├── openrouter_provider.py     # OpenRouter implementation (with fallback model logic)
│   ├── prompts.py                 # Prompt engineering and construction
│   ├── story_generator.py         # Pipeline orchestration (NASA → prompt → AI → validate)
│   ├── chat_service.py            # Multi-turn chat logic
│   ├── bulletin_service.py        # Daily bulletin generation service
│   ├── bulletin_store.py          # JSON-file persistence for generated bulletins
│   ├── scheduler.py               # APScheduler-based daily bulletin scheduler
│   └── test_prompt.py             # Development prompt scratch file
├── tests/                         # Backend pytest test suite
│   ├── conftest.py                # Path setup; adds backend/ to sys.path
│   ├── test_models.py             # Pydantic model validation, field coercion
│   ├── test_prompts.py            # Prompt construction, JSON fence stripping
│   ├── test_stories.py            # Stories archive endpoint
│   ├── test_chat.py               # Multi-turn chat endpoint
│   ├── test_analyze_image.py      # Image upload, MIME validation, vision AI path
│   ├── test_space_weather.py      # DONKI CME data handling
│   ├── test_bulletin_service.py   # Bulletin generation service
│   ├── test_bulletin_store.py     # JSON bulletin persistence
│   ├── test_scheduler.py          # Daily bulletin scheduler
│   ├── test_nasa.py               # NASAClient unit tests
│   ├── test_nasa_integration.py   # NASAClient TTL cache and integration tests
│   └── test_openrouter_fallback.py # OpenRouter fallback model logic tests
├── frontend/                      # Next.js TypeScript application (see below)
│   ├── app/                       # Next.js App Router pages
│   │   ├── page.tsx               # / — Home dashboard
│   │   ├── interpreter/           # /interpreter — Vision AI image analysis
│   │   ├── chat/                  # /chat — AI space chat
│   │   ├── stories/               # /stories — NASA stories archive
│   │   ├── favorites/             # /favorites — Saved favorites
│   │   └── layout.tsx             # Root layout (RTL Arabic, SpaceNav)
│   ├── components/                # React components (dashboard, chat, interpreter, etc.)
│   ├── hooks/                     # useDailyNews, useFavorites, useBulletinStatus
│   ├── lib/                       # api.ts (typed HTTP client), types.ts
│   └── __tests__/                 # Jest test suite (components, hooks, lib)
├── al-tariq-frontend/             # Static HTML/CSS/JS frontend (see below)
│   ├── index.html                 # Home / Morning Bulletin
│   ├── interpreter.html           # Vision AI image upload
│   ├── chat.html                  # AI space conversation
│   ├── stories.html               # NASA/APOD story archive
│   ├── favorites.html             # Local favorites
│   ├── exoplanets.html            # Exoplanet catalog explorer
│   ├── weather.html               # Solar and geomagnetic monitor
│   ├── pulsar-lab.html            # Pulsar physics workbench
│   ├── calendar.html              # Astronomy events calendar
│   ├── observatory.html           # Observatory view
│   ├── mission-timeline.html      # Mission timeline
│   ├── settings.html              # Settings / API proxy placeholder
│   ├── styles.css                 # Shared design system and responsive layout
│   ├── app.js                     # Starfield, i18n, navigation, shared interactions
│   ├── api.js                     # Centralised API client for the FastAPI backend
│   ├── config.js                  # Backend URL configuration (default: localhost:8000)
│   ├── server.js                  # Zero-dependency Node.js static file server
│   └── package.json               # `npm start` shortcut
├── OUR PROMET/                    # IBM Bob development artifacts (see below)
├── requirements.txt               # Python dependencies
├── pytest.ini                     # pytest configuration
├── .env.example                   # Backend environment variable template
├── validate_scheduler_runtime.py  # Runtime validation script for the bulletin scheduler
└── README.md                      # This file
```

---

## Frontend Implementations

This repository currently contains **two frontend implementations**. This is intentional and reflects the project's current MVP stage.

### 1. `frontend/` — Next.js TypeScript application

The original frontend implementation built with Next.js 14, React, TypeScript, and Tailwind CSS. It provides a fully RTL Arabic-language interface covering all core features: the home dashboard, image interpreter, AI chat, stories archive, and favorites. It also includes a full Jest + React Testing Library test suite.

**Use this frontend if you want:** the complete Arabic RTL experience, TypeScript type safety, or to run the frontend test suite.

```bash
# From the frontend/ directory
npm install
cp .env.local.example .env.local   # adjust NEXT_PUBLIC_API_URL if needed
npm run dev
# → http://localhost:3000
```

### 2. `al-tariq-frontend/` — Static HTML/CSS/JS application

A newer static frontend implementation designed specifically for the Al-Tariq experience. It is built with vanilla HTML, CSS, and JavaScript — zero build tooling required. It uses a modern English LTR space-themed design with a rich set of pages including exoplanets, weather, pulsar lab, calendar, and mission timeline — pages not yet present in the Next.js frontend.

The static frontend communicates with the same FastAPI backend through `api.js`, which reads the backend URL from `config.js` (default: `http://localhost:8000`). At the current MVP stage, some pages use placeholder/demo data; integration with real backend endpoints is in progress.

**This is the intended direction for the project's future final production interface.**

**Use this frontend if you want:** the latest design direction, the extended page set, or a demonstration without Node.js build tooling.

```bash
# From the al-tariq-frontend/ directory
npm start
# → http://localhost:3000
```

> Requires only Node.js 18 or newer (no npm install step — zero dependencies).

### Summary comparison

| Aspect | `frontend/` (Next.js) | `al-tariq-frontend/` (Static) |
|---|---|---|
| Technology | Next.js 14 / React / TypeScript | Vanilla HTML / CSS / JavaScript |
| Language / direction | Arabic RTL | English LTR |
| Backend integration | Fully integrated | Core pages integrated; some pages use demo data |
| Test suite | Jest + RTL (see Testing) | None |
| Build required | Yes (`npm install`) | No (`npm start` only) |
| Future direction | Maintained | **Primary direction** |

---

## How to Run the Project

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- A NASA API key — free from [api.nasa.gov](https://api.nasa.gov) (`DEMO_KEY` works for light testing with strict rate limits)
- An OpenRouter API key — free tier at [openrouter.ai](https://openrouter.ai)

---

### Step 1 — Backend

```bash
# From the project root

# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
#    Windows:
.venv\Scripts\activate
#    macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Copy the environment template and fill in your keys
#    Windows:
copy .env.example .env
#    macOS / Linux:
cp .env.example .env
# Open .env and set at minimum: NASA_API_KEY and OPENROUTER_API_KEY

# 5. Start the backend server (run from the project root)
cd backend
python -m uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`.
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

---

### Step 2A — Al-Tariq Static Frontend (recommended for demonstration)

```bash
# From the al-tariq-frontend/ directory
cd al-tariq-frontend
npm start
# → http://localhost:3000
```

No `npm install` step is needed — this frontend has zero npm dependencies.

---

### Step 2B — Next.js Frontend (full Arabic RTL experience)

```bash
# From the frontend/ directory
cd frontend
npm install

# Optional: adjust the backend URL if it differs from http://localhost:8000
#    Windows:
copy .env.local.example .env.local
#    macOS / Linux:
cp .env.local.example .env.local

npm run dev
# → http://localhost:3000
```

> Run only one frontend at a time on port 3000.

---

## Backend API Overview

All endpoints accept and return JSON. Successful responses use the envelope `{"success": true, "data": {...}}`. Error responses use `{"success": false, "error": {"code": "...", "message": "..."}}`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `GET` | `/api/daily-news` | Fetch today's NASA APOD and generate an AI Arabic story |
| `GET` | `/api/daily-news/status` | Scheduler status and latest bulletin metadata |
| `POST` | `/api/analyze` | Analyse a specific APOD date or free-text space context |
| `POST` | `/api/analyze-image` | Upload a space image; returns structured Arabic vision AI analysis |
| `POST` | `/api/chat` | Multi-turn Arabic space AI conversation |
| `GET` | `/api/space-weather` | Real-time NASA DONKI CME space-weather data (no AI dependency) |
| `GET` | `/api/stories` | Paginated APOD story archive (`?count=5&end_date=YYYY-MM-DD`) |

### `POST /api/analyze-image`

Accepts `multipart/form-data`:
- `image` — JPEG, PNG, or WEBP file, max 5 MB (required)
- `question` — optional Arabic question about the image (max 400 characters)

Returns a structured Arabic analysis: title, summary, key observations, scientific explanation, confidence level, and an answer to the user's question (if provided). The image is never stored permanently.

### `POST /api/chat`

Accepts a JSON body with:
- `messages` — array of `{role, content}` objects (max 20 turns; user messages truncated at 800 characters)
- `image_context` — optional object from a previous `/api/analyze-image` call

---

## Environment Variables

Create `.env` in the **project root** by copying `.env.example`. The backend reads this file automatically.

### Core (backend, `/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NASA_API_KEY` | Recommended | `DEMO_KEY` | NASA public API key |
| `OPENROUTER_API_KEY` | **Yes** (AI endpoints) | _(empty)_ | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `google/gemini-2.0-flash-exp:free` | Primary text model slug |
| `OPENROUTER_FALLBACK_MODEL` | No | `meta-llama/llama-3.3-70b-instruct:free` | Fallback text model on rate-limit / 503 |
| `OPENROUTER_VISION_MODEL` | No | `google/gemini-2.0-flash-exp:free` | Vision model slug |
| `OPENROUTER_VISION_FALLBACK_MODEL` | No | _(env-defined)_ | Fallback vision model |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | Override AI API base URL |
| `OPENROUTER_MAX_TOKENS` | No | `2000` | Maximum output tokens |
| `OPENROUTER_MIN_COMPLETION_TOKENS` | No | `100` | Minimum tokens to accept as a valid response |

### NASA tuning

| Variable | Required | Default | Description |
|---|---|---|---|
| `NASA_REQUEST_TIMEOUT` | No | `3` | APOD request timeout in seconds |
| `NASA_DONKI_TIMEOUT` | No | `12` | DONKI request timeout in seconds |
| `NASA_APOD_FALLBACK` | No | `true` | Return placeholder story on APOD timeout instead of hanging |

### Daily bulletin scheduler

| Variable | Required | Default | Description |
|---|---|---|---|
| `DAILY_BULLETIN_ENABLED` | No | `false` | Enable automatic daily bulletin generation |
| `DAILY_BULLETIN_HOUR` | No | `7` | Scheduler hour (0–23) |
| `DAILY_BULLETIN_MINUTE` | No | `0` | Scheduler minute (0–59) |
| `DAILY_BULLETIN_TIMEZONE` | No | `UTC` | IANA timezone for the scheduler |
| `BULLETIN_STORE_PATH` | No | `bulletin_store.json` | Path for the bulletin JSON cache |

### Other

| Variable | Required | Default | Description |
|---|---|---|---|
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `DEBUG` | No | `false` | Enable debug mode |

### Next.js frontend (`/frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend server base URL |

> **Security note:** `NASA_API_KEY` and `OPENROUTER_API_KEY` must be stored in the backend `.env` file only. Never add them to any frontend environment file. All AI and NASA calls are made exclusively by the Python backend.

---

## Testing and Validation

### Backend tests

```bash
# From the project root, with the virtual environment activated
python -m pytest tests/ -v
```

Live tests (those that make real network calls to NASA or OpenRouter) are excluded by default. To run them explicitly:

```bash
python -m pytest tests/ -m live -v
```

Test files cover:

| File | Coverage area |
|---|---|
| `test_models.py` | Pydantic model validation, field coercion, language detection |
| `test_prompts.py` | Prompt construction, JSON fence stripping |
| `test_stories.py` | Stories archive endpoint |
| `test_chat.py` | Multi-turn chat endpoint |
| `test_analyze_image.py` | Image upload, MIME validation, vision AI path |
| `test_space_weather.py` | DONKI CME data handling |
| `test_bulletin_service.py` | Bulletin generation service |
| `test_bulletin_store.py` | JSON bulletin persistence |
| `test_scheduler.py` | Daily bulletin scheduler |
| `test_nasa.py` | NASAClient unit tests (mock network) |
| `test_nasa_integration.py` | NASAClient TTL cache and HTTP integration tests |
| `test_openrouter_fallback.py` | OpenRouter fallback model logic |

### Next.js frontend tests

```bash
# From the frontend/ directory
npm test
```

```bash
# TypeScript type check
npm run type-check
```

```bash
# ESLint
npm run lint
```

### Scheduler runtime validation

A standalone script for end-to-end validation of the daily bulletin scheduler is available at the project root:

```bash
# From the backend/ directory (with virtual environment activated)
python ..\validate_scheduler_runtime.py   # Windows
python ../validate_scheduler_runtime.py   # macOS / Linux
```

This script verifies scheduler startup, bulletin generation, `BulletinStore` persistence, idempotency (duplicate prevention), and that no API keys are present in status responses.

---

## Security

- **API keys are server-side only.** `NASA_API_KEY` and `OPENROUTER_API_KEY` are read by the Python backend at startup and never transmitted to or accessible from the browser.
- **Uploaded images are not stored permanently.** Bytes are read into memory, base64-encoded, sent to the vision model, and then discarded. No file is written to disk.
- **Structured error responses.** All errors use a consistent JSON envelope. Stack traces are never surfaced to clients.
- **Chat input limits.** User messages are truncated server-side at 800 characters; conversation history is capped at 20 turns.
- **Image validation.** Only `image/jpeg`, `image/png`, and `image/webp` are accepted, with a 5 MB size limit enforced before any processing.
- **CORS.** Currently open (`allow_origins=["*"]`) for development. This must be restricted to the specific frontend origin before any production deployment.

---

## Development Process and IBM Bob

Al-Tariq was developed using **IBM Bob** as the primary AI-assisted development environment throughout the project lifecycle.

The repository contains a folder named `OUR PROMET/` which holds development artifacts documenting significant parts of this workflow — including task descriptions, architecture analyses, automation reports, and completion summaries generated during development sessions with IBM Bob. This folder is intentionally preserved in the repository as a transparent record of the AI-assisted development process used for this challenge submission.

The `OUR PROMET/` folder is a development artifact and is not required to run the application.

---

## MVP Status and Future Direction

Al-Tariq is currently an **MVP / prototype**. The core backend and both frontend implementations are functional, but the project is actively evolving.

### What is fully implemented

- FastAPI backend with all documented endpoints
- Pydantic-validated AI output pipeline
- OpenRouter integration with primary and fallback model support
- NASA APOD and DONKI integrations with TTL caching
- Vision AI image analysis endpoint
- Multi-turn chat endpoint
- Daily bulletin scheduler
- Next.js Arabic RTL frontend (all core pages)
- Al-Tariq static frontend (full page set, partial backend integration)
- Backend test suite

### Planned / in progress

- Full backend integration for all `al-tariq-frontend/` pages (some currently show demo data)
- Visual polish and design refinement
- Production hardening: CORS tightening, rate limiting, authentication
- Arabic support and RTL design parity in `al-tariq-frontend/`
- Deployment infrastructure

---

## Team

- **Team Name:** [TO BE COMPLETED]
- **Team Members:** [TO BE COMPLETED]
- **Institution / Organization:** [TO BE COMPLETED]

---

## Challenge Information

- **Challenge Name:** [TO BE COMPLETED]
- **Competition / Event:** [TO BE COMPLETED]
- **Selected Theme:** [TO BE COMPLETED]

---

## Submission Checklist

- [x] Working prototype with functional backend and two frontend implementations
- [x] IBM Bob used as primary AI-assisted development environment throughout the project
- [x] Development artifacts preserved in `OUR PROMET/`
- [ ] IBM SkillsBuild learning activity completed
- [ ] Public GitHub repository URL inserted
- [ ] Public demo video URL inserted
- [ ] Official challenge theme inserted
- [ ] Final screenshots added
- [ ] Team member names and roles verified

---

## License

> No LICENSE file is currently present in the repository.
> Add license information as required by the competition rules before final submission.
