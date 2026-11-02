# Run Al-Tariq on Replit

1. Import `Al-Tariq-Replit-Ready.zip` into a new Replit workspace.
2. In **Secrets**, add `OPENROUTER_API_KEY`. Add `NASA_API_KEY` with a
   personal NASA key for reliable rate limits; `DEMO_KEY` is acceptable for
   light testing.
3. Click **Run**. `.replit` invokes `scripts/start-replit.sh`, which installs
   dependencies when needed, starts FastAPI on the private port 8000, and
   serves Next.js on the public port.
4. Open the Replit web preview and verify `/`, `/stories`, `/interpreter`, and
   `/chat`. Without an OpenRouter key, the dashboard and NASA-only weather
   route can start, while AI actions intentionally show a configuration error.

Optional variables are documented in `.env.example`. For a split deployment,
set `NEXT_PUBLIC_API_URL` to the public backend URL and set
`CORS_ALLOW_ORIGINS` to the frontend origin. Never commit `.env` or secrets.
