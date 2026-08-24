/**
 * Typed HTTP client for the Space Interpreter FastAPI backend.
 * The browser communicates only with this backend — never with NASA or OpenRouter directly.
 * No API keys are used here.
 */

import type {
  DailyNewsResponse,
  StatusResponse,
  SpaceStory,
  StatusData,
  ImageAnalysisResponse,
  ImageAnalysisResult,
  ImageAnalysisSuccess,
  ChatMessage,
  ChatAPIResponse,
  ChatResponseData,
  StoriesResponse,
  StoriesData,
} from './types';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

function getApiBase(): string {
  // NEXT_PUBLIC_API_URL is the only frontend env var — points to the FastAPI backend.
  const base =
    (typeof process !== 'undefined' &&
      process.env.NEXT_PUBLIC_API_URL) ||
    'http://localhost:8000';
  return base.replace(/\/$/, '');
}

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

export class APIClientError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'APIClientError';
  }
}

// ---------------------------------------------------------------------------
// Internal fetch helper
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string): Promise<T> {
  const url = `${getApiBase()}${path}`;
  let res: Response;

  try {
    res = await fetch(url, {
      headers: { Accept: 'application/json' },
      // Cache "no-store" so we always hit the backend — no stale Next.js cache
      cache: 'no-store',
    });
  } catch {
    throw new APIClientError(
      'NETWORK_ERROR',
      'تعذّر الاتصال بالخادم. تحقق من أن الخادم يعمل.',
    );
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new APIClientError(
      'PARSE_ERROR',
      'تعذّر قراءة استجابة الخادم.',
    );
  }

  if (typeof json !== 'object' || json === null) {
    throw new APIClientError('PARSE_ERROR', 'استجابة غير متوقعة من الخادم.');
  }

  const body = json as { success?: boolean; error?: { code: string; message: string } };

  if (!res.ok || body.success === false) {
    const code = body.error?.code ?? `HTTP_${res.status}`;
    // Surface safe human-readable message — never expose backend internals
    const message =
      body.error?.message ?? 'حدث خطأ غير متوقع. يرجى المحاولة مجدداً.';
    throw new APIClientError(code, message);
  }

  return json as T;
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * Fetch today's NASA APOD Arabic space story.
 * May take 5–30 seconds on first load (live NASA + AI generation).
 */
export async function fetchDailyNews(): Promise<SpaceStory> {
  const res = await apiFetch<DailyNewsResponse>('/api/daily-news');
  if (!res.success) {
    throw new APIClientError(res.error.code, res.error.message);
  }
  return res.data;
}

/**
 * Fetch scheduler status and latest bulletin metadata.
 * Fast — no external API calls on the backend side.
 */
export async function fetchStatus(): Promise<StatusData> {
  const res = await apiFetch<StatusResponse>('/api/daily-news/status');
  if (!res.success) {
    throw new APIClientError(res.error.code, res.error.message);
  }
  return res.data;
}

/**
 * Upload an image and optional question to the backend vision analysis endpoint.
 *
 * Uses multipart/form-data — the backend handles all AI calls.
 * No API key is used or accessible on the frontend.
 *
 * @param image   The image File object selected by the user.
 * @param question  Optional Arabic question about the image.
 */
export async function analyzeImage(
  image: File,
  question?: string,
): Promise<ImageAnalysisResult> {
  const url = `${getApiBase()}/api/analyze-image`;

  const formData = new FormData();
  formData.append('image', image);
  if (question && question.trim()) {
    formData.append('question', question.trim());
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header — browser sets it with boundary automatically
      cache: 'no-store',
    });
  } catch {
    throw new APIClientError(
      'NETWORK_ERROR',
      'تعذّر الاتصال بالخادم. تحقق من أن الخادم يعمل.',
    );
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new APIClientError('PARSE_ERROR', 'تعذّر قراءة استجابة الخادم.');
  }

  if (typeof json !== 'object' || json === null) {
    throw new APIClientError('PARSE_ERROR', 'استجابة غير متوقعة من الخادم.');
  }

  const body = json as ImageAnalysisResponse;

  if (!res.ok || body.success === false) {
    const code = (body as { error?: { code: string; message: string } }).error?.code ?? `HTTP_${res.status}`;
    const message =
      (body as { error?: { code: string; message: string } }).error?.message ??
      'حدث خطأ غير متوقع أثناء تحليل الصورة.';
    throw new APIClientError(code, message);
  }

  return (body as ImageAnalysisSuccess).data;
}

/**
 * Send a chat message and receive the AI's reply.
 *
 * @param messages  Full conversation history (role + content).
 * @param imageContext  Optional ImageAnalysisResult to ground the chat.
 */
export async function sendChatMessage(
  messages: ChatMessage[],
  imageContext?: Record<string, unknown> | null,
): Promise<ChatResponseData> {
  const url = `${getApiBase()}/api/chat`;

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        messages,
        image_context: imageContext ?? null,
      }),
      cache: 'no-store',
    });
  } catch {
    throw new APIClientError('NETWORK_ERROR', 'تعذّر الاتصال بالخادم. تحقق من أن الخادم يعمل.');
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new APIClientError('PARSE_ERROR', 'تعذّر قراءة استجابة الخادم.');
  }

  if (typeof json !== 'object' || json === null) {
    throw new APIClientError('PARSE_ERROR', 'استجابة غير متوقعة من الخادم.');
  }

  const body = json as ChatAPIResponse;
  if (!res.ok || body.success === false) {
    const code = (body as { error?: { code: string; message: string } }).error?.code ?? `HTTP_${res.status}`;
    const message =
      (body as { error?: { code: string; message: string } }).error?.message ??
      'حدث خطأ غير متوقع في المحادثة.';
    throw new APIClientError(code, message);
  }

  return (body as { success: true; data: ChatResponseData }).data;
}

/**
 * Fetch a list of APOD stories for browsing/archive.
 *
 * @param count     Number of days (1–10).
 * @param endDate   End date YYYY-MM-DD. Defaults to today.
 */
export async function fetchStories(count = 5, endDate?: string): Promise<StoriesData> {
  let path = `/api/stories?count=${count}`;
  if (endDate) path += `&end_date=${endDate}`;

  const res = await apiFetch<StoriesResponse>(path);
  if (!res.success) {
    throw new APIClientError(res.error.code, res.error.message);
  }
  return res.data;
}
