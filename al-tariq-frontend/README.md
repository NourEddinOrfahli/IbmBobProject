# Al-Tariq — Space Interpreter

Static frontend handoff for the 2026 astronomy experience.

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
- `server.js` — zero-dependency local static server
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

This is intentionally a frontend-only handoff. Replace the demo data and `setTimeout` handlers later with the documented backend calls:

- `GET /api/daily-news`
- `GET /api/stories`
- `POST /api/chat`
- `POST /api/analyze-image`

NASA and OpenRouter credentials must remain server-side. The UI is English LTR by design, with no client-side API keys.