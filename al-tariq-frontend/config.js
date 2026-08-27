/**
 * Al-Tariq frontend — backend configuration.
 *
 * Set AL_TARIQ_API_URL in the server environment, or override window.AL_TARIQ_API_URL
 * from a server-rendered meta tag, to point at a different backend host.
 *
 * Default: http://localhost:8000  (FastAPI dev server)
 */

// Allow runtime override via a global set by the static server (for production deploys).
// Falls back to the standard local FastAPI port.
window.AL_TARIQ_API_URL =
  (typeof window !== 'undefined' && window.AL_TARIQ_API_URL) ||
  'http://localhost:8000';
