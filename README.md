# النجم الطارق — Al-Tariq

### AI-Powered Arabic Space Interpreter

**Team:** 404Found

---

## One-Sentence Pitch

Al-Tariq helps Arabic-speaking users understand astronomy and space content by combining NASA real-time data, AI-generated Arabic scientific explanations, conversational space AI, and vision-based image analysis into a single integrated platform.

---

## Problem Statement

Astronomy content and astronomical images are difficult for non-specialists to access, especially when information is scattered across technical sources and almost always presented in English. This leaves billions of Arabic speakers with limited access to one of humanity's most exciting fields of knowledge.

Specifically:

- **Accessible Arabic explanations are rare.** Most NASA publications, APOD captions, and space-weather bulletins are in English and use specialised scientific vocabulary.
- **Astronomical images lack contextual interpretation.** When someone encounters a space image, there is no easy way to ask "what is this?" in Arabic and receive a scientifically grounded answer.
- **There is no conversational AI focused on Arabic space education.** General-purpose chatbots are not tuned for Arabic space literacy or for discussing specific images.
- **Space data is scattered.** APOD, DONKI space-weather events, and archived stories live in separate places with no unified Arabic interface.

---

## Solution

Al-Tariq addresses this problem by building a unified platform that connects NASA's public APIs, an OpenRouter-powered AI layer, and a Next.js Arabic frontend into one coherent experience.

The implemented system provides:

- **Daily NASA APOD content** fetched live and rendered with full Arabic AI-generated interpretation.
- **NASA DONKI space-weather data** (Coronal Mass Ejection events) integrated into the same bulletin to give real-time space-weather context alongside the daily story.
- **AI-generated Arabic scientific stories** produced by a large language model with prompt engineering enforcing Arabic output, scientific accuracy, and structured JSON.
- **Conversational space AI chat** — multi-turn Arabic chat about astronomy topics.
- **Image upload and Vision AI analysis** — users upload any space image; the backend sends it to a multimodal vision model and returns a structured Arabic interpretation (title, summary, observations, scientific explanation, confidence level, and an answer to the user's specific question).
- **NASA stories archive** — paginated browsing of past APOD entries with load-more functionality.
- **Favorites** — client-side favorites backed by LocalStorage.
- **A fully RTL Arabic interface** that is responsive and works on mobile.

All AI calls are made server-side. No API keys are ever exposed to the browser.

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
| Story search | Client-side filtering within the stories page |
| Load more stories | Loads additional entries going further back in time |
| Favorites | LocalStorage-based favorites across pages |
| RTL Arabic interface | `<html lang="ar" dir="rtl">` throughout |
| Responsive/mobile interface | Tailwind CSS responsive layout |

### Application Routes

| Route | Page |
|---|---|
| `/` | Home dashboard (APOD story + space weather) |
| `/interpreter` | Image upload and Vision AI analysis |
| `/chat` | AI space chat |
| `/stories` | NASA stories archive with search |
| `/favorites` | Saved favorites |

> The current interface is functional and responsive; visual polishing and design refinement may be performed separately by the team before the final presentation.

---

## AI Approach & Architecture

### System Overview

```
User
 ↓
Next.js Frontend (TypeScript / React)
 ↓
FastAPI Backend (Python)
 ↓
 ┌──────────────────────┐
 │  NASA APIs           │
 │  APOD + DONKI        │
 └──────────────────────┘
 ↓
AI / OpenRouter
 ↓
 ┌──────────────┬──────────────┬──────────────┐
 │  Story       │  Chat        │  Vision      │
 │  Generation  │              │  Analysis    │
 └──────────────┴──────────────┴──────────────┘
 ↓
Pydantic-validated result
 ↓
Next.js Frontend
```

### Text AI Path

1. The frontend calls `GET /api/daily-news` or `POST /api/analyze`.
2. `NASAClient` fetches the APOD data and, optionally, DONKI CME events.
3. `prompts.py` builds a structured system + user prompt enforcing Arabic output and a specific JSON schema.
4. `OpenRouterProvider.generate_structured_response()` calls the OpenRouter API with the prompt.
5. The raw response is parsed (including stripping markdown fences if present).
6. `SpaceStory` (Pydantic model) validates the structure; a `model_validator` also checks that the language tag matches the actual script of the generated text.
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
 → vision model: nvidia/nemotron-nano-12b-v2-vl:free
 → raw JSON response parsed
 → ImageAnalysisResult (Pydantic) validated
 → Arabic structured result returned to frontend
```

The vision model in use is `nvidia/nemotron-nano-12b-v2-vl:free`, which replaced the originally configured model after it was found to be unavailable during live verification.

### NASA Data Path

- **APOD** — `NASAClient.get_apod(apod_date?)` calls `https://api.nasa.gov/planetary/apod`. The response is normalised into a `NASAAPODData` Pydantic model. APOD is required; the pipeline returns an error if it is unavailable.
- **DONKI** — `NASAClient.get_space_weather()` calls `https://api.nasa.gov/DONKI/CME`. DONKI is non-fatal; if it is unavailable, the story is still generated using APOD data only.

### Validation & Safety Layer

- All AI output is validated via Pydantic models (`SpaceStory`, `ImageAnalysisResult`).
- A `model_validator` on `SpaceStory` corrects the `language` field if the AI returns English content while claiming `"language": "ar"`.
- `field_validator` on `confidence` normalises values to `high | medium | low`.
- Image MIME type is checked against an allowlist (`image/jpeg`, `image/png`, `image/webp`).
- Image size is enforced at 5 MB maximum.
- Chat messages are truncated server-side at 800 characters; history is capped at 20 turns.
- API keys are never exposed to the frontend. The only frontend environment variable is `NEXT_PUBLIC_API_URL`.
- All error responses use a structured `{"success": false, "error": {"code": "...", "message": "..."}}` envelope; stack traces are never surfaced.

---

## IBM Bob Usage

IBM Bob was the **primary development tool** used to build Al-Tariq from the ground up.

> Important distinction: IBM Bob is the development AI assistant used to write and verify this project. NASA APIs and OpenRouter are external third-party services integrated into the project — they are not part of IBM Bob.

Bob's verified contributions throughout the project:

| Area | Bob's Role |
|---|---|
| **Architecture** | Designed the full-stack architecture: provider abstraction, pipeline structure, frontend component tree |
| **Backend implementation** | Wrote all Python source files: `main.py`, `config.py`, `models.py`, `nasa_client.py`, `ai_provider.py`, `openrouter_provider.py`, `prompts.py`, `story_generator.py`, `chat_service.py`, `bulletin_service.py`, `bulletin_store.py`, `scheduler.py` |
| **NASA API integration** | Implemented async HTTP client (`nasa_client.py`) for APOD and DONKI with timeout handling and structured model output |
| **OpenRouter integration** | Implemented `OpenRouterProvider` with retry logic, JSON fence stripping, and minimum token validation |
| **AI prompt engineering** | Designed Arabic-first prompts with structured JSON schema enforcement and scientific accuracy constraints |
| **Vision AI integration** | Implemented `analyze_image` endpoint: MIME/size validation, base64 encoding, multimodal OpenRouter request, Pydantic validation of vision output |
| **Frontend implementation** | Built all Next.js pages and React components in TypeScript with Tailwind CSS: dashboard, interpreter, chat, stories, favorites |
| **UI/UX implementation** | Built RTL Arabic interface, responsive layout, component state handling |
| **Testing — Backend** | Wrote all pytest test files covering models, prompts, NASA client, chat, image analysis, scheduler, bulletin service/store |
| **Testing — Frontend** | Wrote all Jest/React Testing Library tests for components, hooks, and API client |
| **Debugging** | Investigated and resolved failures across all layers including NASA API edge cases, AI model routing issues, vision model fallback |
| **Integration verification** | Ran automated test suites across all layers; performed live HTTP verification of the Vision AI endpoint; verified frontend production build |
| **Final validation** | Verified 308/308 backend tests pass, 121/121 frontend tests pass, TypeScript compiles clean, ESLint passes, and production build succeeds |
| **Documentation** | Wrote this README |

---

## Selected Challenge Theme

> **TODO:** Insert the exact official challenge theme name before submission.

---

## Technology Stack

### Frontend

| Technology | Purpose |
|---|---|
| Next.js 14 | React framework, routing, image optimisation |
| React 18 | UI component library |
| TypeScript 5 | Static typing |
| Tailwind CSS 3 | Utility-first styling and responsive layout |

### Backend

| Technology | Purpose |
|---|---|
| Python 3.11+ | Primary backend language |
| FastAPI | REST API framework with async support |
| Pydantic v2 | Data validation and serialisation |
| httpx | Async HTTP client (NASA API calls) |
| APScheduler | Optional daily bulletin scheduler |
| python-multipart | Multipart form handling for image upload |
| uvicorn | ASGI server |

### AI

| Technology | Purpose |
|---|---|
| OpenRouter | AI gateway providing access to multiple models |
| `meta-llama/llama-3.3-70b-instruct:free` | Default text model for Arabic story generation |
| `nvidia/nemotron-nano-12b-v2-vl:free` | Vision model for image analysis (verified live) |

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

## Project Structure

```
.                              # Project root
├── backend/                   # Python FastAPI application
│   ├── main.py                # FastAPI app, all endpoints, lifecycle
│   ├── config.py              # Environment-based configuration (dataclasses)
│   ├── models.py              # All Pydantic models (NASA, AI output, API envelopes)
│   ├── nasa_client.py         # Async HTTP client for APOD and DONKI
│   ├── ai_provider.py         # Abstract AIProvider interface
│   ├── openrouter_provider.py # OpenRouter implementation of AIProvider
│   ├── prompts.py             # All prompt engineering and construction
│   ├── story_generator.py     # Pipeline orchestration (NASA → prompt → AI → validate)
│   ├── chat_service.py        # Multi-turn chat logic
│   ├── bulletin_service.py    # Daily bulletin generation service
│   ├── bulletin_store.py      # JSON-file persistence for generated bulletins
│   └── scheduler.py          # APScheduler-based daily bulletin scheduler
├── tests/                     # Backend pytest test suite
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_prompts.py
│   ├── test_stories.py
│   ├── test_chat.py
│   ├── test_analyze_image.py
│   ├── test_space_weather.py
│   ├── test_bulletin_service.py
│   ├── test_bulletin_store.py
│   └── test_scheduler.py
├── frontend/                  # Next.js TypeScript application
│   ├── app/                   # Next.js App Router pages
│   │   ├── page.tsx           # / — Home dashboard
│   │   ├── interpreter/       # /interpreter — Vision AI image analysis
│   │   ├── chat/              # /chat — AI space chat
│   │   ├── stories/           # /stories — NASA stories archive
│   │   ├── favorites/         # /favorites — Saved favorites
│   │   └── layout.tsx         # Root layout (RTL Arabic, SpaceNav)
│   ├── components/            # React components
│   │   ├── dashboard/         # SpaceDashboard, MorningBulletinHero, SpaceWeatherSection, etc.
│   │   ├── chat/              # SpaceChat
│   │   ├── image-analyzer/    # ImageAnalyzer
│   │   ├── stories/           # StoriesSection
│   │   ├── favorites/         # FavoritesSection
│   │   ├── navigation/        # SpaceNav
│   │   ├── states/            # BulletinEmpty, BulletinError, BulletinSkeleton
│   │   └── ui/                # APODImage, CMEEventCard, ConfidenceBadge, KeyFact, etc.
│   ├── hooks/                 # useDailyNews, useFavorites, useBulletinStatus
│   ├── lib/                   # api.ts (typed HTTP client), types.ts
│   └── __tests__/             # Jest test suite (components, hooks, lib)
├── requirements.txt           # Python dependencies
├── pytest.ini                 # pytest configuration
├── .env.example               # Backend environment variable template
└── README.md                  # This file
```

---

## How to Run Locally

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- A NASA API key — free from [api.nasa.gov](https://api.nasa.gov) (`DEMO_KEY` works for light testing)
- An OpenRouter API key — free tier at [openrouter.ai](https://openrouter.ai)

### Backend

```bash
# From the project root

# 1. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the environment template and fill in your keys
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# Edit .env — set NASA_API_KEY and OPENROUTER_API_KEY

# 4. Start the backend server
cd backend
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`.  
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### Frontend

```bash
# From the frontend/ directory

# 1. Install dependencies
npm install

# 2. Copy the environment template
copy .env.local.example .env.local     # Windows
# cp .env.local.example .env.local    # macOS/Linux
# Edit .env.local if your backend runs on a different port

# 3. Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

> **Security note:** API keys (`NASA_API_KEY`, `OPENROUTER_API_KEY`) must be stored in the backend `.env` file only. Never add them to `frontend/.env.local`. The only frontend variable is `NEXT_PUBLIC_API_URL`, which points to the backend server — it contains no secrets.

---

## Environment Variables

### Backend (`/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NASA_API_KEY` | Recommended | `DEMO_KEY` | NASA public API key |
| `OPENROUTER_API_KEY` | **Yes** (AI endpoints) | _(empty)_ | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `meta-llama/llama-3.3-70b-instruct:free` | Text model slug |
| `OPENROUTER_VISION_MODEL` | No | `nvidia/nemotron-nano-12b-v2-vl:free` | Vision model slug |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | Override API base URL |
| `OPENROUTER_MAX_TOKENS` | No | `2000` | Maximum output tokens |
| `OPENROUTER_MIN_COMPLETION_TOKENS` | No | `100` | Minimum tokens to accept as a valid response |
| `DAILY_BULLETIN_ENABLED` | No | `false` | Enable automatic daily story scheduler |
| `DAILY_BULLETIN_HOUR` | No | `7` | Scheduler hour (0–23) |
| `DAILY_BULLETIN_MINUTE` | No | `0` | Scheduler minute (0–59) |
| `DAILY_BULLETIN_TIMEZONE` | No | `UTC` | IANA timezone for scheduler |
| `BULLETIN_STORE_PATH` | No | `bulletin_store.json` | Path for bulletin JSON cache |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `DEBUG` | No | `false` | Enable debug mode |

### Frontend (`/frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend server base URL |

> **Never** expose `NASA_API_KEY` or `OPENROUTER_API_KEY` via `NEXT_PUBLIC_*` variables. All AI and NASA calls are made by the backend.

---

## Testing & Verification

### Backend

```bash
# From the project root (with .venv activated)
python -m pytest tests/ -v
```

**Result: 308/308 tests passed**

Test files:

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

### Frontend

```bash
# From the frontend/ directory
npm test
```

**Result: 121/121 tests passed**

```bash
# TypeScript type check
npm run type-check
```

**Result: PASS**

```bash
# ESLint
npm run lint
```

**Result: PASS**

```bash
# Production build
npm run build
```

**Result: PASS**

### Live Vision AI Verification

| Item | Result |
|---|---|
| Vision AI endpoint (`POST /api/analyze-image`) | ✅ VERIFIED |
| Vision model | `nvidia/nemotron-nano-12b-v2-vl:free` |
| Note | The originally configured vision model was found to be unavailable during live verification and was replaced with `nvidia/nemotron-nano-12b-v2-vl:free`, which was verified live. |

---

## Security

The following security measures are implemented and present in the codebase:

- **API keys are server-side only.** `NASA_API_KEY` and `OPENROUTER_API_KEY` are read by the Python backend at startup. They are never sent to or accessible from the browser.
- **No secrets in frontend source or build.** The only `NEXT_PUBLIC_*` variable is `NEXT_PUBLIC_API_URL`, which contains only the backend server address — no credentials.
- **Uploaded image MIME validation.** Only `image/jpeg`, `image/png`, and `image/webp` are accepted. Unsupported types return a `422` error before any processing.
- **Uploaded image size limit.** Files larger than 5 MB are rejected before encoding or transmission to the AI provider.
- **Images are not stored permanently.** Uploaded bytes are read into memory, base64-encoded, sent to the vision model, and then discarded. No file is written to disk.
- **Structured error responses.** All errors use a `{"success": false, "error": {"code": "...", "message": "..."}}` envelope. Stack traces are never exposed to the client.
- **Chat input truncation.** User messages are truncated server-side at 800 characters and conversation history is capped at 20 turns.
- **CORS configuration.** The FastAPI backend configures `CORSMiddleware` with `allow_origins=["*"]` and `allow_methods=["GET", "POST"]`. This is currently open for development convenience; it should be tightened to the specific frontend origin before production deployment.

---

## Current Status

Al-Tariq is functionally implemented and has passed the automated and live verification described in this README:

- ✅ 308/308 backend tests passing
- ✅ 121/121 frontend tests passing
- ✅ TypeScript clean
- ✅ ESLint clean
- ✅ Production build passing
- ✅ Vision AI live-verified

> The current interface is functional and responsive; visual polishing and design refinement may be performed separately by the team before the final presentation.

---

## Demo

### Demo Video

> TODO — insert public demo video URL

### GitHub Repository

> TODO — insert public GitHub repository URL

---

## Screenshots

> TODO: Add final product screenshots before submission.

---

## Team

**Team Name:** 404Found

> TODO: Add verified team member names and roles.

---

## License

> TODO: Add license information if required by the competition.
> No LICENSE file is currently present in the repository.

---

## Competition Submission Checklist

- [x] Working prototype (functional implementation verified)
- [x] IBM Bob used as primary development tool throughout the project
- [ ] IBM SkillsBuild learning activity completed
- [ ] Public GitHub repository URL
- [ ] Public demo video
- [ ] Official challenge theme inserted
- [ ] Final screenshots added
- [ ] Verified team member names and roles
