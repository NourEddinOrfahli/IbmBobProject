/**
 * Al-Tariq — centralized API client for the Space Interpreter FastAPI backend.
 *
 * All backend communication goes through this module.
 * No NASA or OpenRouter keys are used here — everything stays server-side.
 *
 * Backend base URL comes from config.js (window.AL_TARIQ_API_URL).
 * Default: http://localhost:8000
 */

/* ─── helpers ─────────────────────────────────────────────────────────────── */

function _base() {
  return (window.AL_TARIQ_API_URL || 'http://localhost:8000').replace(/\/$/, '');
}

/**
 * Generic fetch wrapper that normalises the backend {success, data} envelope.
 * Throws an Error with a human-readable `.message` on any failure.
 */
async function _apiFetch(path, options = {}) {
  const url = _base() + path;
  let res;
  try {
    res = await fetch(url, { cache: 'no-store', ...options });
  } catch {
    throw new Error('Cannot reach the backend. Make sure the FastAPI server is running.');
  }

  let json;
  try {
    json = await res.json();
  } catch {
    throw new Error('Unexpected response from server (not JSON).');
  }

  if (!res.ok || json.success === false) {
    const msg = json?.error?.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return json.data;
}

/* ─── public API ──────────────────────────────────────────────────────────── */

/**
 * GET /api/daily-news
 * Returns the AI-generated SpaceStory for today's NASA APOD.
 * May take 5–30 seconds on first call.
 * @returns {Promise<SpaceStory>}
 */
async function fetchDailyNews() {
  return _apiFetch('/api/daily-news');
}

/**
 * GET /api/daily-news/status
 * Returns scheduler metadata and latest bulletin info. Fast — no external calls.
 * @returns {Promise<StatusData>}
 */
async function fetchDailyNewsStatus() {
  return _apiFetch('/api/daily-news/status');
}

/**
 * GET /api/stories?count=N&end_date=YYYY-MM-DD
 * Returns a list of NASA APOD entries. No AI call — pure data.
 * @param {number} count   1–10
 * @param {string} [endDate]  YYYY-MM-DD, defaults to today
 * @returns {Promise<{stories: StoryCard[], count: number}>}
 */
async function fetchStories(count = 10, endDate) {
  let path = `/api/stories?count=${count}`;
  if (endDate) path += `&end_date=${encodeURIComponent(endDate)}`;
  return _apiFetch(path);
}

/**
 * POST /api/analyze-image
 * Sends a space image (multipart/form-data) to the vision AI.
 * @param {File}   imageFile   JPEG/PNG/WEBP, max 5 MB
 * @param {string} [question]  Optional question (max 400 chars)
 * @returns {Promise<ImageAnalysisResult>}
 */
async function analyzeImage(imageFile, question) {
  const formData = new FormData();
  formData.append('image', imageFile);          // field name must be exactly "image"
  if (question && question.trim()) {
    formData.append('question', question.trim()); // field name must be exactly "question"
  }
  // Do NOT set Content-Type — the browser sets it with the correct boundary.
  return _apiFetch('/api/analyze-image', { method: 'POST', body: formData });
}

/**
 * POST /api/chat
 * Multi-turn space AI chat. Stateless — pass the full history each time.
 * @param {Array<{role: string, content: string}>} messages  Full conversation history
 * @param {object|null} [imageContext]  Optional ImageAnalysisResult from analyzeImage()
 * @returns {Promise<{reply: string, role: string}>}
 */
async function sendChatMessage(messages, imageContext) {
  // Sanitise image_context — only the five keys the backend forwards
  let safeContext = null;
  if (imageContext) {
    safeContext = {};
    for (const key of ['title', 'summary', 'observations', 'scientific_explanation', 'confidence']) {
      if (imageContext[key] !== undefined) safeContext[key] = imageContext[key];
    }
  }

  return _apiFetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ messages, image_context: safeContext }),
  });
}

/**
 * GET /api/space-weather
 * Returns real NASA DONKI CME data as a SpaceWeatherSummary.
 * No AI or OpenRouter dependency — works independently of daily-news.
 * @returns {Promise<SpaceWeatherSummary>}
 */
async function fetchSpaceWeather() {
  return _apiFetch('/api/space-weather');
}

/**
 * GET /health
 * Quick liveness probe.
 * @returns {Promise<{status: string}>}
 */
async function checkHealth() {
  const url = _base() + '/health';
  const res = await fetch(url, { cache: 'no-store' });
  return res.json();
}

/* ─── expose as globals ────────────────────────────────────────────────────── */
// The frontend pages load this script with <script src="api.js"> and call these
// functions directly — no module bundler required.
window.AlTariqAPI = {
  fetchDailyNews,
  fetchDailyNewsStatus,
  fetchStories,
  analyzeImage,
  sendChatMessage,
  fetchSpaceWeather,
  checkHealth,
};
