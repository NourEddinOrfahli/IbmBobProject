/**
 * TypeScript interfaces mirroring the Space Interpreter backend API contracts.
 * Derived from backend/models.py — do not add fields not in the backend schema.
 */

// ---------------------------------------------------------------------------
// Space weather (DONKI CME passthrough)
// ---------------------------------------------------------------------------

export interface CMEEventSummary {
  event_type: string;
  begin_time: string | null;
  speed_kmps: number | null;
  is_earth_directed: boolean | null;
  estimated_arrival: string | null;
  kp_index: number | null;
  source_location: string | null;
  note: string | null;
}

export interface SpaceWeatherSummary {
  available: boolean;
  event_count: number;
  events: CMEEventSummary[];
}

// ---------------------------------------------------------------------------
// NASA APOD source provenance
// ---------------------------------------------------------------------------

export interface SourceData {
  source: string;        // Always "NASA APOD"
  date: string;          // "YYYY-MM-DD"
  title: string;         // Original English APOD title
  media_type: string;    // "image" | "video"
  image_url: string | null;
  hd_image_url: string | null;
  copyright: string | null;
}

// ---------------------------------------------------------------------------
// AI-generated Arabic space story
// ---------------------------------------------------------------------------

export interface SpaceStory {
  title: string;
  summary: string;
  scientific_explanation: string;
  key_facts: string[];
  why_it_matters: string;
  story: string;
  source_data: SourceData;
  confidence: 'high' | 'medium' | 'low' | string;
  language: string;  // "ar" | "en"
  space_weather: SpaceWeatherSummary | null;
}

// ---------------------------------------------------------------------------
// Scheduler / bulletin status
// ---------------------------------------------------------------------------

export interface SchedulerInfo {
  enabled: boolean;
  last_run: string | null;
  last_success: string | null;
  apod_date: string | null;
  status: 'success' | 'failed' | 'skipped' | null;
}

export interface LatestBulletin {
  apod_date: string;
  status: 'success' | 'failed';
  generated_at: string;
}

export interface StatusData {
  scheduler: SchedulerInfo;
  latest_bulletin: LatestBulletin | null;
}

// ---------------------------------------------------------------------------
// API response envelopes
// ---------------------------------------------------------------------------

export interface DailyNewsSuccess {
  success: true;
  data: SpaceStory;
}

export interface StatusSuccess {
  success: true;
  data: StatusData;
}

export interface APIError {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type DailyNewsResponse = DailyNewsSuccess | APIError;
export type StatusResponse = StatusSuccess | APIError;

// ---------------------------------------------------------------------------
// Image analysis (POST /api/analyze-image)
// ---------------------------------------------------------------------------

export interface ImageAnalysisResult {
  title: string;
  summary: string;
  observations: string[];
  scientific_explanation: string;
  confidence: 'high' | 'medium' | 'low' | string;
  story: string;
  question_answer: string;
  is_space_related: boolean;
}

export interface ImageAnalysisSuccess {
  success: true;
  data: ImageAnalysisResult;
}

export type ImageAnalysisResponse = ImageAnalysisSuccess | APIError;

// ---------------------------------------------------------------------------
// Chat (POST /api/chat)
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponseData {
  reply: string;
  role: string;
}

export interface ChatSuccess {
  success: true;
  data: ChatResponseData;
}

export type ChatAPIResponse = ChatSuccess | APIError;

// ---------------------------------------------------------------------------
// Stories (GET /api/stories)
// ---------------------------------------------------------------------------

export interface StoryCard {
  id: string;           // APOD date YYYY-MM-DD
  date: string;
  title: string;
  summary: string;
  image_url: string | null;
  hd_image_url: string | null;
  media_type: string;
  copyright: string | null;
  source: string;
}

export interface StoriesData {
  stories: StoryCard[];
  count: number;
}

export interface StoriesSuccess {
  success: true;
  data: StoriesData;
}

export type StoriesResponse = StoriesSuccess | APIError;
