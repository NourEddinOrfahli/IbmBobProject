# Al-Tariq — Space Interpreter

Canonical bilingual frontend for the 2026 astronomy experience.

## Included

- `index.html` — Home / Morning Bulletin
- `interpreter.html` — Vision AI image upload and result state
- `chat.html` — AI space conversation
- `stories.html` — NASA/APOD story archive with search, filters, and load-more state
- `favorites.html` — local favorites archive
- `exoplanets.html` — exoplanet catalog explorer
- `weather.html` — solar and geomagnetic monitor
- `pulsar-lab.html` — interactive pulsar physics workbench
- `calendar.html` — astronomy events calendar
- `settings.html` — system settings and API proxy placeholder
- `styles.css` — shared cosmic design system and responsive layout
- `app.js` — demo interactions and localStorage favorites
- `server.js` — zero-dependency static server and same-origin FastAPI proxy
- `package.json` — `npm start` shortcut

## Run locally

Requires Node.js 18 or newer:

```bash
npm start
```

Then open `http://localhost:3000`.

You can also open `index.html` directly, but using the local server is
recommended because it behaves more like a real frontend deployment.

## Frontend integration notes

The primary pages use the existing FastAPI backend through same-origin
relative requests. Exploratory simulation pages intentionally retain their
local demo data and do not claim to be live NASA observations.

- `GET /api/daily-news`
- `GET /api/stories`
- `POST /api/chat`
- `POST /api/analyze-image`

NASA and OpenRouter credentials remain server-side. The AR/EN switcher is
persisted in `localStorage` and updates page direction between RTL and LTR.