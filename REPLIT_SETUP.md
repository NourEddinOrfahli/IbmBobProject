# Run Al-Tariq on Replit

1. Import `Al-Tariq-Modern-Frontend-Replit.zip` into a new Replit workspace.
2. In **Secrets**, add `OPENROUTER_API_KEY`. Add `NASA_API_KEY` with a
   personal NASA key for reliable rate limits; `DEMO_KEY` is acceptable for
   light testing.
3. Click **Run**. `.replit` invokes `scripts/start-replit.sh`, which starts
   FastAPI on private `127.0.0.1:8000`, waits for `/health`, and then serves
   `al-tariq-frontend/` on the public Replit `PORT`.
4. Open the Replit web preview and verify `/`, `/stories.html`,
   `/interpreter.html`, `/chat.html`, `/health`, and `/api/space-weather`.
   Without an OpenRouter key, NASA-only routes can start while AI actions
   intentionally show a configuration error.

Optional variables are documented in `.env.example`. The Node proxy accepts
`BACKEND_HOST`, `BACKEND_PORT`, and `PORT`; `AL_TARIQ_API_URL` is only needed
for an intentional split deployment. Never commit `.env` or secrets.
