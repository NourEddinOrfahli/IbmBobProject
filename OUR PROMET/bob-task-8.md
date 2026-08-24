# You are continuing development of the existing Space Interpreter project.

IMPORTANT:
This is TASK 2 of the AI experience implementation.

The existing application is already working and verified:
- Backend: FastAPI
- Frontend: Next.js + TypeScript
- NASA APOD integration works
- NASA DONKI / space-weather integration works
- OpenRouter AI provider works
- Arabic scientific story generation works
- Existing dashboard works
- Backend tests: 227/227 passing
- Frontend tests: 57/57 passing
- TypeScript: passing
- Production build: passing
- ESLint: passing

DO NOT redesign or replace the existing architecture.
DO NOT remove existing functionality.
DO NOT break the existing dashboard.
DO NOT expose API keys to the frontend.
DO NOT add unnecessary dependencies.
DO NOT implement unrelated features.

==================================================
GOAL
==================================================

Implement the second major AI capability:

USER IMAGE → VISION ANALYSIS → SPACE INTERPRETATION

The user must be able to upload an image related to space and optionally ask a question about it.

Examples:

1. User uploads an image without a question:
   "Analyze this space image."

2. User uploads an image and asks:
   "شو عم شوف بهالصورة؟"

3. User uploads an image and asks:
   "هل هذا كوكب أم نجم؟ اشرحلي."

4. User uploads an image and asks:
   "اكتبلي قصة قصيرة مستوحاة من هذه الصورة، لكن لا تخترع حقائق علمية."

The system should analyze the image and return a useful Arabic scientific interpretation.

==================================================
PHASE 1 — INVESTIGATE BEFORE CODING
==================================================

First inspect the existing project.

Identify:
- current OpenRouter provider
- current AI provider abstraction
- current story generator
- current prompts
- backend models
- frontend API client
- frontend types
- existing dashboard architecture
- existing dependencies

Determine the smallest clean implementation that fits the current architecture.

Do NOT immediately modify files.

First produce a short implementation plan internally, then implement it.

==================================================
PHASE 2 — BACKEND IMAGE ANALYSIS API
==================================================

Add a dedicated backend endpoint for image interpretation.

Preferred API:

POST /api/analyze-image

Use multipart/form-data.

Inputs:
- image: uploaded image file
- question: optional text question

Supported image types should be restricted to safe common formats:
- JPEG
- PNG
- WEBP

Implement:
- MIME/type validation
- reasonable maximum file size
- clear errors for unsupported files
- safe temporary handling
- do not permanently store user images unless absolutely required
- clean up temporary files/resources after processing

The endpoint must never expose:
- OpenRouter API keys
- NASA API keys
- internal prompts
- internal stack traces

==================================================
PHASE 3 — VISION MODEL
==================================================

Inspect the existing OpenRouter integration and determine whether the current provider can support multimodal/image input.

Prefer using an OpenRouter-supported vision-capable model if this can be done cleanly within the existing provider abstraction.

Do NOT hard-code an expensive paid model.

Prefer a currently accessible/free or low-cost vision-capable model when available.

If the existing provider abstraction needs a small extension to support image input, extend it cleanly instead of creating a completely separate AI architecture.

The vision model should receive:
- the uploaded image
- the optional user question
- a strict system instruction

The model should NOT be asked to expose hidden chain-of-thought.

Ask it only for the final structured result.

==================================================
PHASE 4 — STRUCTURED AI RESPONSE
==================================================

The AI response must be structured JSON.

Create an appropriate Pydantic response model.

Suggested conceptual structure:

{
  "title": "...",
  "summary": "...",
  "observations": [
    "...",
    "..."
  ],
  "scientific_explanation": "...",
  "confidence": "high|medium|low",
  "story": "...",
  "question_answer": "..."
}

Adapt the exact fields to the existing project's terminology and architecture.

Important distinction:

OBSERVATIONS:
Only describe what can reasonably be observed from the image.

SCIENTIFIC EXPLANATION:
Explain the likely scientific meaning without presenting uncertain identification as fact.

QUESTION ANSWER:
Answer the user's question if one was provided.

STORY:
Provide an engaging Arabic story only when appropriate.

The AI must clearly distinguish:
- observed information
- inferred information
- uncertain identification

Never invent NASA mission data, object names, dates, measurements, distances, or scientific facts simply because they sound plausible.

==================================================
PHASE 5 — NASA DATA SAFETY
==================================================

If the image itself contains identifiable NASA/APOD information, do not blindly assume that every claim is verified.

The image analysis is primarily visual.

If existing NASA data is needed for verification, use the existing backend NASA integrations where appropriate.

Do not invent NASA verification.

For uncertain visual identification, say that the identification is uncertain.

==================================================
PHASE 6 — PROMPT ENGINEERING
==================================================

Create a dedicated vision prompt in the existing prompts architecture.

The system role should establish:

You are "Space Interpreter", an Arabic scientific space interpreter.

Your job is to help ordinary users understand space-related images.

Rules:
1. Analyze only what the image supports.
2. Never fabricate scientific facts.
3. Separate observation from interpretation.
4. Explicitly communicate uncertainty.
5. Answer the user's question directly when provided.
6. Use accessible Arabic.
7. Preserve scientific accuracy.
8. Do not reveal internal reasoning or hidden chain-of-thought.
9. Do not claim NASA verification unless actual NASA data was used.
10. If the image is not space-related, clearly say so instead of forcing a space interpretation.

Use structured JSON output.

==================================================
PHASE 7 — FRONTEND IMAGE EXPERIENCE
==================================================

Add a clean Arabic RTL image-analysis interface.

The user should be able to:

- select an image
- see a preview before sending
- optionally type a question
- click "حلّل الصورة"
- see loading state
- see errors clearly
- see the resulting analysis

The UI should match the existing Space Interpreter visual identity.

Do NOT redesign the existing dashboard.

Create a dedicated component/page/section that can later be integrated into the main navigation.

Suggested UI:

┌──────────────────────────────────────┐
│          🔭 حلّل صورة فضائية         │
│                                      │
│      [ Drag & Drop / اختر صورة ]     │
│                                      │
│            Image Preview             │
│                                      │
│  ماذا تريد أن تعرف عن هذه الصورة؟    │
│  [______________________________]    │
│                                      │
│          [ 🔍 حلّل الصورة ]          │
└──────────────────────────────────────┘

Then display:

العنوان

ملخص

ما الذي نراه؟
• observation
• observation

🔬 التفسير العلمي

💬 إجابة سؤالك

📖 القصة

🎯 مستوى الثقة

==================================================
PHASE 8 — FRONTEND API
==================================================

Extend the existing typed API layer.

Do not call OpenRouter or NASA directly from frontend.

Frontend must communicate only with the backend.

No API key may appear anywhere in:
- frontend source
- NEXT_PUBLIC variables
- browser network requests
- client bundles

==================================================
PHASE 9 — ERROR HANDLING
==================================================

Handle:

- no image selected
- unsupported file type
- image too large
- malformed upload
- vision model unavailable
- OpenRouter error
- timeout
- invalid AI JSON
- empty AI response
- non-space image
- uncertain visual identification

Show friendly Arabic error messages.

Never expose raw exceptions to the user.

==================================================
PHASE 10 — TESTS
==================================================

Add backend tests for:

- valid image upload
- invalid MIME type
- oversized image
- missing image
- optional question
- structured AI response validation
- malformed AI response
- AI provider failure
- safe error handling

Add frontend tests for:

- image selection
- image preview
- question input
- submit/loading state
- successful result rendering
- error rendering
- no-image validation

Run the complete existing test suites.

The existing tests must continue passing.

Target:

Backend:
227 existing tests + new tests = all passing

Frontend:
57 existing tests + new tests = all passing

Also run:
- TypeScript
- ESLint
- production build

==================================================
PHASE 11 — SECURITY
==================================================

Perform a security review of the new implementation.

Check specifically:
- API key exposure
- arbitrary file upload
- dangerous file types
- excessive image size
- temporary file cleanup
- path traversal
- prompt injection through image/question
- raw exception leakage
- logging of user images or sensitive data

Do not log image contents or API keys.

==================================================
IMPORTANT IMPLEMENTATION RULES
==================================================

1. Do not modify unrelated files.
2. Do not remove existing features.
3. Do not replace OpenRouter.
4. Do not replace the current NASA pipeline.
5. Do not redesign the current dashboard.
6. Reuse existing abstractions wherever possible.
7. Keep the implementation modular.
8. Use TypeScript types on the frontend.
9. Use Pydantic models on the backend.
10. Keep all Arabic UI RTL.
11. Do not expose chain-of-thought.
12. Do not hallucinate scientific facts.
13. Do not claim an image is definitely a specific astronomical object unless the evidence supports it.
14. Do not use a paid model when a suitable accessible model can perform the task.
15. Do not leave development servers running from your command execution.

==================================================
FINAL VERIFICATION
==================================================

After implementation:

1. Run backend tests.
2. Run frontend tests.
3. Run TypeScript check.
4. Run ESLint.
5. Run production build.
6. Verify the new endpoint with a short-lived test.
7. Verify frontend → backend image upload integration.
8. Verify API keys are absent from frontend/build output.

At the end provide a concise report containing:

- files created
- files modified
- new API endpoint
- vision model selected and why
- prompt architecture
- security measures
- backend test result
- frontend test result
- TypeScript result
- ESLint result
- production build result
- any remaining limitations

Do NOT start implementing a chat history system, authentication, database persistence, or unrelated features in this task.

This task is ONLY:
IMAGE UPLOAD + VISION ANALYSIS + OPTIONAL USER QUESTION + ARABIC SPACE INTERPRETATION.

---

**Status:** error  **Date:** 2026-08-21

---

### 👤 User

You are continuing development of the existing Space Interpreter project.

IMPORTANT:
This is TASK 2 of the AI experience implementation.

The existing application is already working and verified:
- Backend: FastAPI
- Frontend: Next.js + TypeScript
- NASA APOD integration works
- NASA DONKI / space-weather integration works
- OpenRouter AI provider works
- Arabic scientific story generation works
- Existing dashboard works
- Backend tests: 227/227 passing
- Frontend tests: 57/57 passing
- TypeScript: passing
- Production build: passing
- ESLint: passing

DO NOT redesign or replace the existing architecture.
DO NOT remove existing functionality.
DO NOT break the existing dashboard.
DO NOT expose API keys to the frontend.
DO NOT add unnecessary dependencies.
DO NOT implement unrelated features.

==================================================
GOAL
==================================================

Implement the second major AI capability:

USER IMAGE → VISION ANALYSIS → SPACE INTERPRETATION

The user must be able to upload an image related to space and optionally ask a question about it.

Examples:

1. User uploads an image without a question:
   "Analyze this space image."

2. User uploads an image and asks:
   "شو عم شوف بهالصورة؟"

3. User uploads an image and asks:
   "هل هذا كوكب أم نجم؟ اشرحلي."

4. User uploads an image and asks:
   "اكتبلي قصة قصيرة مستوحاة من هذه الصورة، لكن لا تخترع حقائق علمية."

The system should analyze the image and return a useful Arabic scientific interpretation.

==================================================
PHASE 1 — INVESTIGATE BEFORE CODING
==================================================

First inspect the existing project.

Identify:
- current OpenRouter provider
- current AI provider abstraction
- current story generator
- current prompts
- backend models
- frontend API client
- frontend types
- existing dashboard architecture
- existing dependencies

Determine the smallest clean implementation that fits the current architecture.

Do NOT immediately modify files.

First produce a short implementation plan internally, then implement it.

==================================================
PHASE 2 — BACKEND IMAGE ANALYSIS API
==================================================

Add a dedicated backend endpoint for image interpretation.

Preferred API:

POST /api/analyze-image

Use multipart/form-data.

Inputs:
- image: uploaded image file
- question: optional text question

Supported image types should be restricted to safe common formats:
- JPEG
- PNG
- WEBP

Implement:
- MIME/type validation
- reasonable maximum file size
- clear errors for unsupported files
- safe temporary handling
- do not permanently store user images unless absolutely required
- clean up temporary files/resources after processing

The endpoint must never expose:
- OpenRouter API keys
- NASA API keys
- internal prompts
- internal stack traces

==================================================
PHASE 3 — VISION MODEL
==================================================

Inspect the existing OpenRouter integration and determine whether the current provider can support multimodal/image input.

Prefer using an OpenRouter-supported vision-capable model if this can be done cleanly within the existing provider abstraction.

Do NOT hard-code an expensive paid model.

Prefer a currently accessible/free or low-cost vision-capable model when available.

If the existing provider abstraction needs a small extension to support image input, extend it cleanly instead of creating a completely separate AI architecture.

The vision model should receive:
- the uploaded image
- the optional user question
- a strict system instruction

The model should NOT be asked to expose hidden chain-of-thought.

Ask it only for the final structured result.

==================================================
PHASE 4 — STRUCTURED AI RESPONSE
==================================================

The AI response must be structured JSON.

Create an appropriate Pydantic response model.

Suggested conceptual structure:

{
  "title": "...",
  "summary": "...",
  "observations": [
    "...",
    "..."
  ],
  "scientific_explanation": "...",
  "confidence": "high|medium|low",
  "story": "...",
  "question_answer": "..."
}

Adapt the exact fields to the existing project's terminology and architecture.

Important distinction:

OBSERVATIONS:
Only describe what can reasonably be observed from the image.

SCIENTIFIC EXPLANATION:
Explain the likely scientific meaning without presenting uncertain identification as fact.

QUESTION ANSWER:
Answer the user's question if one was provided.

STORY:
Provide an engaging Arabic story only when appropriate.

The AI must clearly distinguish:
- observed information
- inferred information
- uncertain identification

Never invent NASA mission data, object names, dates, measurements, distances, or scientific facts simply because they sound plausible.

==================================================
PHASE 5 — NASA DATA SAFETY
==================================================

If the image itself contains identifiable NASA/APOD information, do not blindly assume that every claim is verified.

The image analysis is primarily visual.

If existing NASA data is needed for verification, use the existing backend NASA integrations where appropriate.

Do not invent NASA verification.

For uncertain visual identification, say that the identification is uncertain.

==================================================
PHASE 6 — PROMPT ENGINEERING
==================================================

Create a dedicated vision prompt in the existing prompts architecture.

The system role should establish:

You are "Space Interpreter", an Arabic scientific space interpreter.

Your job is to help ordinary users understand space-related images.

Rules:
1. Analyze only what the image supports.
2. Never fabricate scientific facts.
3. Separate observation from interpretation.
4. Explicitly communicate uncertainty.
5. Answer the user's question directly when provided.
6. Use accessible Arabic.
7. Preserve scientific accuracy.
8. Do not reveal internal reasoning or hidden chain-of-thought.
9. Do not claim NASA verification unless actual NASA data was used.
10. If the image is not space-related, clearly say so instead of forcing a space interpretation.

Use structured JSON output.

==================================================
PHASE 7 — FRONTEND IMAGE EXPERIENCE
==================================================

Add a clean Arabic RTL image-analysis interface.

The user should be able to:

- select an image
- see a preview before sending
- optionally type a question
- click "حلّل الصورة"
- see loading state
- see errors clearly
- see the resulting analysis

The UI should match the existing Space Interpreter visual identity.

Do NOT redesign the existing dashboard.

Create a dedicated component/page/section that can later be integrated into the main navigation.

Suggested UI:

┌──────────────────────────────────────┐
│          🔭 حلّل صورة فضائية         │
│                                      │
│      [ Drag & Drop / اختر صورة ]     │
│                                      │
│            Image Preview             │
│                                      │
│  ماذا تريد أن تعرف عن هذه الصورة؟    │
│  [______________________________]    │
│                                      │
│          [ 🔍 حلّل الصورة ]          │
└──────────────────────────────────────┘

Then display:

العنوان

ملخص

ما الذي نراه؟
• observation
• observation

🔬 التفسير العلمي

💬 إجابة سؤالك

📖 القصة

🎯 مستوى الثقة

==================================================
PHASE 8 — FRONTEND API
==================================================

Extend the existing typed API layer.

Do not call OpenRouter or NASA directly from frontend.

Frontend must communicate only with the backend.

No API key may appear anywhere in:
- frontend source
- NEXT_PUBLIC variables
- browser network requests
- client bundles

==================================================
PHASE 9 — ERROR HANDLING
==================================================

Handle:

- no image selected
- unsupported file type
- image too large
- malformed upload
- vision model unavailable
- OpenRouter error
- timeout
- invalid AI JSON
- empty AI response
- non-space image
- uncertain visual identification

Show friendly Arabic error messages.

Never expose raw exceptions to the user.

==================================================
PHASE 10 — TESTS
==================================================

Add backend tests for:

- valid image upload
- invalid MIME type
- oversized image
- missing image
- optional question
- structured AI response validation
- malformed AI response
- AI provider failure
- safe error handling

Add frontend tests for:

- image selection
- image preview
- question input
- submit/loading state
- successful result rendering
- error rendering
- no-image validation

Run the complete existing test suites.

The existing tests must continue passing.

Target:

Backend:
227 existing tests + new tests = all passing

Frontend:
57 existing tests + new tests = all passing

Also run:
- TypeScript
- ESLint
- production build

==================================================
PHASE 11 — SECURITY
==================================================

Perform a security review of the new implementation.

Check specifically:
- API key exposure
- arbitrary file upload
- dangerous file types
- excessive image size
- temporary file cleanup
- path traversal
- prompt injection through image/question
- raw exception leakage
- logging of user images or sensitive data

Do not log image contents or API keys.

==================================================
IMPORTANT IMPLEMENTATION RULES
==================================================

1. Do not modify unrelated files.
2. Do not remove existing features.
3. Do not replace OpenRouter.
4. Do not replace the current NASA pipeline.
5. Do not redesign the current dashboard.
6. Reuse existing abstractions wherever possible.
7. Keep the implementation modular.
8. Use TypeScript types on the frontend.
9. Use Pydantic models on the backend.
10. Keep all Arabic UI RTL.
11. Do not expose chain-of-thought.
12. Do not hallucinate scientific facts.
13. Do not claim an image is definitely a specific astronomical object unless the evidence supports it.
14. Do not use a paid model when a suitable accessible model can perform the task.
15. Do not leave development servers running from your command execution.

==================================================
FINAL VERIFICATION
==================================================

After implementation:

1. Run backend tests.
2. Run frontend tests.
3. Run TypeScript check.
4. Run ESLint.
5. Run production build.
6. Verify the new endpoint with a short-lived test.
7. Verify frontend → backend image upload integration.
8. Verify API keys are absent from frontend/build output.

At the end provide a concise report containing:

- files created
- files modified
- new API endpoint
- vision model selected and why
- prompt architecture
- security measures
- backend test result
- frontend test result
- TypeScript result
- ESLint result
- production build result
- any remaining limitations

Do NOT start implementing a chat history system, authentication, database persistence, or unrelated features in this task.

This task is ONLY:
IMAGE UPLOAD + VISION ANALYSIS + OPTIONAL USER QUESTION + ARABIC SPACE INTERPRETATION.

---

### 🤖 Assistant

> 🔧 called: update_todo_list, list_files, list_files, list_files, list_files, read_file, read_file, read_file, read_file, read_file, read_file, read_file, list_files, list_files, read_file, read_file, list_files, list_files, list_files, list_files, read_file



> 🔧 **update_todo_list** — 
[-] Phase 1: Investigate existing project architecture
[ ] Phase 2: Backend image analysis API endpoint
[ ] Phase 3: Vision model integration
[ ] Phase 4: Structured AI response (Pydantic model)
[ ] Phase 5: NASA data safety considerations
[ ] Phase 6: Prompt engineering for vision
[ ] Phase 7: Frontend image analysis UI component
[ ] Phase 8: Frontend API layer extension
[ ] Phase 9: Error handling
[ ] Phase 10: Tests (backend + frontend)
[ ] Phase 11: Security review
[ ] Final verification (tests, TypeScript, ESLint, build)


> 🔧 **list_files** — .

> 🔧 **list_files** — backend

> 🔧 **list_files** — frontend

> 🔧 **list_files** — tests

> 🔧 **read_file** — backend/ai_provider.py

> 🔧 **read_file** — backend/models.py

> 🔧 **read_file** — backend/prompts.py

> 🔧 **read_file** — backend/openrouter_provider.py

> 🔧 **list_files** — frontend/__tests__

> 🔧 **list_files** — frontend/components

> 🔧 **read_file** — frontend/lib

> 🔧 **read_file** — backend/config.py

> 🔧 **read_file** — backend/main.py

> 🔧 **list_files** — frontend/components/dashboard

> 🔧 **list_files** — frontend/__tests__/components

> 🔧 **list_files** — frontend/app

> 🔧 **list_files** — frontend/__tests__/lib

> 🔧 **read_file** — backend/story_generator.py

> 🔧 **read_file** — frontend/lib/types.ts

> 🔧 **read_file** — frontend/lib/api.ts

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file, read_file, read_file, read_file, read_file, read_file, read_file

Now let me read the existing tests and front-end components to understand the full picture:

> 🔧 **read_file** — frontend/jest.config.js

> 🔧 **read_file** — frontend/app/page.tsx

> 🔧 **read_file** — frontend/package.json

> 🔧 **read_file** — frontend/app/layout.tsx

> 🔧 **read_file** — tests/test_models.py

> 🔧 **read_file** — frontend/tailwind.config.js

> 🔧 **read_file** — frontend/__tests__/lib/api.test.ts

> 🔧 **read_file** — frontend/components/dashboard/SpaceDashboard.tsx

> 🔧 **read_file** — tests/test_prompts.py

> 🔧 **read_file** — frontend/__tests__/components/APODImage.test.tsx

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file, read_file, update_todo_list

Now I have a thorough understanding of the project. Let me check the requirements.txt and read the conftest.py:

> 🔧 **read_file** — requirements.txt

> 🔧 **read_file** — frontend/components/dashboard/MorningBulletinHero.tsx

> 🔧 **read_file** — tests/conftest.py

> 🔧 **read_file** — frontend/app/globals.css

> 🔧 **update_todo_list** — 
[x] Phase 1: Investigate existing project architecture
[-] Phase 2: Backend image analysis API endpoint
[ ] Phase 3: Vision model integration
[ ] Phase 4: Structured AI response (Pydantic model)
[ ] Phase 5: NASA data safety considerations
[ ] Phase 6: Prompt engineering for vision
[ ] Phase 7: Frontend image analysis UI component
[ ] Phase 8: Frontend API layer extension
[ ] Phase 9: Error handling
[ ] Phase 10: Tests (backend + frontend)
[ ] Phase 11: Security review
[ ] Final verification (tests, TypeScript, ESLint, build)


### 🤖 Assistant

> 🔧 called: update_todo_list

Now I have a complete picture of the project. Let me plan the implementation:

**Architecture plan:**
1. **Backend**: Add `ImageAnalysis` Pydantic model + `VISION_SYSTEM_PROMPT` + `build_vision_prompt()` in prompts + extend `OpenRouterProvider` with `analyze_image_with_vision()` + new `POST /api/analyze-image` endpoint
2. **Vision model**: Use `meta-llama/llama-3.2-11b-vision-instruct:free` (free OpenRouter vision model) - falls back to `google/gemini-flash-1.5-8b` if needed
3. **Frontend**: New `ImageAnalyzer` component + extend `api.ts` + extend `types.ts`
4. **Tests**: New backend test file + frontend test file

Let me now implement all phases simultaneously:

> 🔧 **update_todo_list** — 
[x] Phase 1: Investigate existing project architecture
[-] Phase 2: Backend - Pydantic model (ImageAnalysisResult)
[-] Phase 3: Backend - Vision prompt in prompts.py
[-] Phase 4: Backend - Extend OpenRouterProvider with vision support
[ ] Phase 5: Backend - POST /api/analyze-image endpoint in main.py
[ ] Phase 6: Frontend - types.ts extension
[ ] Phase 7: Frontend - api.ts extension
[ ] Phase 8: Frontend - ImageAnalyzer component
[ ] Phase 9: Backend tests for analyze-image
[ ] Phase 10: Frontend tests for ImageAnalyzer
[ ] Phase 11: Security review
[ ] Final verification (tests, TypeScript, ESLint, build)


### 🤖 Assistant

> 🔧 called: apply_diff

Now I'll implement everything. Starting with backend changes:

> 🔧 **apply_diff** — backend/models.py

### 🤖 Assistant

> 🔧 called: apply_diff

Now add the vision prompt to prompts.py:

> 🔧 **apply_diff** — backend/prompts.py

### 🤖 Assistant

> 🔧 called: apply_diff

Now extend the `OpenRouterProvider` with vision/multimodal support and extend `AIProvider` abstract base:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:27
-------
class AIProvider(ABC):
    """Abstract base class for all AI provider implementations."""

    @abstractmethod
    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a prompt to the underlying model and return a parsed JSON dict.

        Parameters
        ----------
        system_prompt:
            The system-role message that configures the AI's behaviour.
        user_prompt:
            The user-role message containing the actual request.
        max_tokens:
            Maximum number of tokens the model may generate.
        temperature:
            Sampling temperature (0 = deterministic, 1 = very creative).

        Returns
        -------
        dict
            Parsed JSON from the model response.

        Raises
        ------
        AIProviderError
            On connection failure, model error, or unparseable output.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any resources held by the provider (e.g. HTTP clients)."""
        ...
=======
class AIProvider(ABC):
    """Abstract base class for all AI provider implementations."""

    @abstractmethod
    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a prompt to the underlying model and return a parsed JSON dict.

        Parameters
        ----------
        system_prompt:
            The system-role message that configures the AI's behaviour.
        user_prompt:
            The user-role message containing the actual request.
        max_tokens:
            Maximum number of tokens the model may generate.
        temperature:
            Sampling temperature (0 = deterministic, 1 = very creative).

        Returns
        -------
        dict
            Parsed JSON from the model response.

        Raises
        ------
        AIProviderError
            On connection failure, model error, or unparseable output.
        """
        ...

    @abstractmethod
    async def analyze_image(
        self,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send an image (base64-encoded) plus text prompt to a vision-capable model
        and return a parsed JSON dict.

        Parameters
        ----------
        image_b64:
            Base64-encoded image content (no data-URI prefix).
        image_mime:
            MIME type string, e.g. "image/jpeg".
        system_prompt:
            System-role message.
        user_prompt:
            User-role text accompanying the image.
        max_tokens:
            Maximum tokens for the response.
        temperature:
            Sampling temperature.

        Returns
        -------
        dict
            Parsed JSON from the model response.

        Raises
        ------
        AIProviderError
            On connection failure, model error, or unparseable output.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any resources held by the provider (e.g. HTTP clients)."""
        ...
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now extend the `OpenRouterProvider` to implement `analyze_image` with vision model support:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:19
-------
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from ai_provider import AIProvider, AIProviderError
from config import OpenRouterConfig
from prompts import build_retry_user_prompt, RETRY_SYSTEM_PROMPT
=======
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from ai_provider import AIProvider, AIProviderError
from config import OpenRouterConfig
from prompts import build_retry_user_prompt, RETRY_SYSTEM_PROMPT

# Vision-capable model to use for image analysis.
# Uses a free, multimodal-capable model on OpenRouter.
# Can be overridden via OPENROUTER_VISION_MODEL env var.
_VISION_MODEL = "meta-llama/llama-3.2-11b-vision-instruct:free"
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:167
-------
    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()
=======
    async def analyze_image(
        self,
        image_b64: str,
        image_mime: str,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1500,
        temperature: float = 0.4,
    ) -> dict[str, Any]:
        """
        Send a multimodal request (image + text) to a vision-capable model.

        Uses a dedicated vision model configured via _VISION_MODEL.
        The image is embedded as a base64 data-URI in the OpenAI vision format.
        """
        import os
        vision_model = os.getenv("OPENROUTER_VISION_MODEL", _VISION_MODEL)

        # Build multimodal user message per OpenAI vision spec
        multimodal_content: list[dict[str, Any]] = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime};base64,{image_b64}",
                },
            },
            {
                "type": "text",
                "text": user_prompt,
            },
        ]

        payload: dict[str, Any] = {
            "model": vision_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": multimodal_content},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        logger.debug(
            "POST %s vision request (model=%s, max_tokens=%d)",
            self._COMPLETIONS_PATH,
            vision_model,
            max_tokens,
        )

        try:
            response = await self._client.post(self._COMPLETIONS_PATH, json=payload)
        except httpx.TimeoutException:
            raise AIProviderError(
                "AI_TIMEOUT",
                f"Vision request timed out after {self._config.request_timeout}s.",
            )
        except httpx.RequestError as exc:
            raise AIProviderError(
                "AI_NETWORK_ERROR",
                f"Network error reaching OpenRouter (vision): {exc}",
            )

        self._check_response_status(response)
        self._log_response_usage(response)

        content, finish_reason = self._extract_content_and_finish_reason(response)
        self._log_finish_reason(finish_reason, attempt=1)

        if finish_reason == "length":
            raise AIProviderError(
                "AI_TRUNCATED",
                "Vision model response was truncated (finish_reason=length). "
                "The image analysis could not be completed.",
            )

        self._validate_response_content(content)
        return self._parse_json_response(content)

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.aclose()
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now add the `OPENROUTER_VISION_MODEL` config key and update `requirements.txt` for `python-multipart`:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:41
-------
    request_timeout: float = 60.0
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MAX_TOKENS", "2000"))
    )
    temperature: float = 0.4
    # Minimum completion tokens required to be considered a real AI response.
    # Responses shorter than this are almost certainly classifier outputs,
    # safety-only responses, or empty replies — never valid story JSON.
    min_completion_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MIN_COMPLETION_TOKENS", "100"))
    )
=======
    request_timeout: float = 60.0
    max_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MAX_TOKENS", "2000"))
    )
    temperature: float = 0.4
    # Minimum completion tokens required to be considered a real AI response.
    # Responses shorter than this are almost certainly classifier outputs,
    # safety-only responses, or empty replies — never valid story JSON.
    min_completion_tokens: int = field(
        default_factory=lambda: int(os.getenv("OPENROUTER_MIN_COMPLETION_TOKENS", "100"))
    )
    # Vision model used for image analysis (multimodal).
    # Defaults to a free vision-capable model on OpenRouter.
    vision_model: str = field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_VISION_MODEL",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
        )
    )
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now add `python-multipart` to requirements.txt (needed for FastAPI file uploads):

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:1
-------
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pydantic>=2.7.0
python-dotenv>=1.0.0
apscheduler>=3.10.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
=======
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
pydantic>=2.7.0
python-dotenv>=1.0.0
apscheduler>=3.10.0
python-multipart>=0.0.9
pytest>=8.0.0
pytest-asyncio>=0.23.0
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now add the `POST /api/analyze-image` endpoint to main.py:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:1
-------
"""
Space Interpreter — FastAPI application entry point.

Endpoints:
  GET  /health                  — liveness probe
  GET  /api/daily-news          — fetch today's APOD and generate an Arabic space story
  GET  /api/daily-news/status   — scheduler and latest bulletin status
  POST /api/analyze             — analyse a specific APOD date or free-text context
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bulletin_service import BulletinService
from bulletin_store import BulletinStore
from config import get_config, validate_config
from models import (
    AnalyzeRequest,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    SuccessResponse,
)
from nasa_client import NASAClient
from scheduler import DailyBulletinScheduler
from story_generator import StoryGenerator, StoryGeneratorError
=======
"""
Space Interpreter — FastAPI application entry point.

Endpoints:
  GET  /health                  — liveness probe
  GET  /api/daily-news          — fetch today's APOD and generate an Arabic space story
  GET  /api/daily-news/status   — scheduler and latest bulletin status
  POST /api/analyze             — analyse a specific APOD date or free-text context
  POST /api/analyze-image       — analyse a user-uploaded space image with vision AI
"""

from __future__ import annotations

import base64
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from bulletin_service import BulletinService
from bulletin_store import BulletinStore
from config import get_config, validate_config
from models import (
    AnalyzeRequest,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ImageAnalysisResult,
    SuccessResponse,
)
from nasa_client import NASAClient
from scheduler import DailyBulletinScheduler
from story_generator import StoryGenerator, StoryGeneratorError
from ai_provider import AIProviderError
from prompts import get_vision_system_prompt, build_vision_user_prompt
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:284
-------
@app.post(
    "/api/analyze",
    response_model=SuccessResponse,
    summary="Analyse a specific APOD date or custom space context",
    tags=["Space"],
)
async def analyze(body: AnalyzeRequest) -> JSONResponse:
    """
    Accepts an optional ``apod_date`` (ISO-8601) and/or ``extra_context``.

    Behaviour:
    - If only ``apod_date`` is provided → fetch that date's APOD and generate a story.
    - If only ``extra_context`` is provided → generate a story from the free-text.
    - If both are provided → fetch APOD and enrich the prompt with extra_context.
    - If neither is provided → default to today's APOD (same as /api/daily-news).
    """
    generator = _require_story_generator()

    try:
        has_date = bool(body.apod_date)
        has_context = bool(body.extra_context)

        if has_context and not has_date:
            story = await generator.generate_from_context(body.extra_context)  # type: ignore[arg-type]
        elif has_date or not has_context:
            # covers: date-only, date+context, or neither (→ today)
            story = await generator.generate_apod_story_with_context(
                body.apod_date, body.extra_context
            )
        else:
            story = await generator.generate_daily_story()

    except StoryGeneratorError as exc:
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /api/analyze")
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content=SuccessResponse(data=story.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )
=======
@app.post(
    "/api/analyze",
    response_model=SuccessResponse,
    summary="Analyse a specific APOD date or custom space context",
    tags=["Space"],
)
async def analyze(body: AnalyzeRequest) -> JSONResponse:
    """
    Accepts an optional ``apod_date`` (ISO-8601) and/or ``extra_context``.

    Behaviour:
    - If only ``apod_date`` is provided → fetch that date's APOD and generate a story.
    - If only ``extra_context`` is provided → generate a story from the free-text.
    - If both are provided → fetch APOD and enrich the prompt with extra_context.
    - If neither is provided → default to today's APOD (same as /api/daily-news).
    """
    generator = _require_story_generator()

    try:
        has_date = bool(body.apod_date)
        has_context = bool(body.extra_context)

        if has_context and not has_date:
            story = await generator.generate_from_context(body.extra_context)  # type: ignore[arg-type]
        elif has_date or not has_context:
            # covers: date-only, date+context, or neither (→ today)
            story = await generator.generate_apod_story_with_context(
                body.apod_date, body.extra_context
            )
        else:
            story = await generator.generate_daily_story()

    except StoryGeneratorError as exc:
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /api/analyze")
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content=SuccessResponse(data=story.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Image analysis constants
# ---------------------------------------------------------------------------

# Supported MIME types for image upload
_ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Maximum upload size: 5 MB (in bytes)
_MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@app.post(
    "/api/analyze-image",
    response_model=SuccessResponse,
    summary="Analyse a user-uploaded space image with vision AI",
    tags=["Space"],
)
async def analyze_image(
    image: UploadFile = File(..., description="Space image to analyse (JPEG, PNG, WEBP)"),
    question: Optional[str] = Form(
        default=None,
        description="Optional Arabic question about the image (max 400 characters)",
    ),
) -> JSONResponse:
    """
    Accepts a multipart/form-data upload with an image file and optional question.

    - Validates MIME type and file size.
    - Encodes the image as base64 and sends it to the vision AI model.
    - Returns a structured Arabic space interpretation.

    Never stores the uploaded image permanently.
    Never exposes API keys, internal prompts, or stack traces.
    """
    if _story_generator is None:
        return _error_response(
            "AI_NOT_CONFIGURED",
            "خدمة الذكاء الاصطناعي غير مهيأة. يرجى الاتصال بمسؤول النظام.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # --- Validate MIME type ---
    content_type = (image.content_type or "").lower().split(";")[0].strip()
    if content_type not in _ALLOWED_IMAGE_MIME_TYPES:
        return _error_response(
            "UNSUPPORTED_IMAGE_TYPE",
            "نوع الملف غير مدعوم. يُرجى رفع صورة بتنسيق JPEG أو PNG أو WEBP.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # --- Read image and enforce size limit ---
    try:
        image_bytes = await image.read()
    except Exception:  # noqa: BLE001
        return _error_response(
            "IMAGE_READ_ERROR",
            "تعذّرت قراءة الصورة المرفوعة. يرجى المحاولة مجدداً.",
            status.HTTP_400_BAD_REQUEST,
        )

    if len(image_bytes) == 0:
        return _error_response(
            "EMPTY_IMAGE",
            "الصورة المرفوعة فارغة.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if len(image_bytes) > _MAX_IMAGE_SIZE_BYTES:
        return _error_response(
            "IMAGE_TOO_LARGE",
            f"حجم الصورة يتجاوز الحد الأقصى المسموح ({_MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} ميغابايت).",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    # --- Base64-encode (no temp file written) ---
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # --- Build prompts ---
    system_prompt = get_vision_system_prompt()
    user_prompt = build_vision_user_prompt(question)

    # --- Call vision AI ---
    try:
        raw_json = await _story_generator._ai.analyze_image(
            image_b64=image_b64,
            image_mime=content_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=config.openrouter.max_tokens,
            temperature=config.openrouter.temperature,
        )
    except AIProviderError as exc:
        logger.error("Vision AI error: %s — %s", exc.code, exc.message)
        return _error_response(exc.code, exc.message, status.HTTP_502_BAD_GATEWAY)
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error calling vision AI")
        return _error_response(
            "INTERNAL_ERROR",
            "حدث خطأ غير متوقع أثناء تحليل الصورة. يرجى المحاولة مجدداً.",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # --- Validate response with Pydantic ---
    try:
        result = ImageAnalysisResult(**raw_json)
    except ValidationError as exc:
        logger.error("ImageAnalysisResult validation failed: %s", exc)
        return _error_response(
            "VALIDATION_ERROR",
            "استجابة الذكاء الاصطناعي لم تطابق الهيكل المتوقع. يرجى المحاولة مجدداً.",
            status.HTTP_502_BAD_GATEWAY,
        )

    return JSONResponse(
        content=SuccessResponse(data=result.model_dump()).model_dump(),
        status_code=status.HTTP_200_OK,
    )
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now let's extend the frontend types and API:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:103
-------
export type DailyNewsResponse = DailyNewsSuccess | APIError;
export type StatusResponse = StatusSuccess | APIError;
=======
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
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

Now extend `api.ts` with the `analyzeImage` function:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:7
-------
import type { DailyNewsResponse, StatusResponse, SpaceStory, StatusData } from './types';
=======
import type {
  DailyNewsResponse,
  StatusResponse,
  SpaceStory,
  StatusData,
  ImageAnalysisResponse,
  ImageAnalysisResult,
} from './types';
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:40
-------
async function apiFetch<T>(path: string): Promise<T> {
  const url = `${getApiBase()}${path}`;
  let res: Response;

  try {
    res = await fetch(url, {
      headers: { Accept: 'application/json' },
      // Cache "no-store" so we always hit the backend — no stale Next.js cache
      cache: 'no-store',
    });
  } catch (networkError) {
    throw new APIClientError(
      'NETWORK_ERROR',
      'تعذّر الاتصال بالخادم. تحقق من أن الخادم يعمل.',
    );
  }
=======
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
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:109
-------
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
=======
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

// Import for return type — already imported above
import type { ImageAnalysisSuccess } from './types';
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: apply_diff

The duplicate import at the bottom won't compile. Let me fix that:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:3
-------
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
} from './types';
=======
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
} from './types';
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:175
-------
  return (body as ImageAnalysisSuccess).data;
}

// Import for return type — already imported above
import type { ImageAnalysisSuccess } from './types';
=======
  return (body as ImageAnalysisSuccess).data;
}
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: write_file

Now create the `ImageAnalyzer` React component:

> 🔧 **write_file** — frontend/components/image-analyzer/ImageAnalyzer.tsx

### 🤖 Assistant

> 🔧 called: write_file

Now write the backend tests for analyze-image:

> 🔧 **write_file** — tests/test_analyze_image.py

### 🤖 Assistant

> 🔧 called: write_file

Now write the frontend tests:

> 🔧 **write_file** — /**
 * Tests for the ImageAnalyzer component.
 *
 * Covers:
 * - Image selection via file input
 * - Image preview rendering
 * - Question input interaction
 * - Submit/loading state
 * - Successful result rendering
 * - Error rendering
 * - No-image validation (submit disabled)
 * - Drop zone rendered initially
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageAnalyzer from '@/components/image-analyzer/ImageAnalyzer';
import { analyzeImage, APIClientError } from '@/lib/api';

// ---------------------------------------------------------------------------
// Mock the API
// ---------------------------------------------------------------------------

jest.mock('@/lib/api', () => ({
  analyzeImage: jest.fn(),
  APIClientError: class APIClientError extends Error {
    code: string;
    constructor(code: string, message: string) {
      super(message);
      this.code = code;
      this.name = 'APIClientError';
    }
  },
}));

const mockAnalyzeImage = analyzeImage as jest.MockedFunction<typeof analyzeImage>;

// ---------------------------------------------------------------------------
// Mock URL.createObjectURL / URL.revokeObjectURL
// ---------------------------------------------------------------------------

const mockObjectUrl = 'blob:http://localhost/mock-image-url';
global.URL.createObjectURL = jest.fn(() => mockObjectUrl);
global.URL.revokeObjectURL = jest.fn();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeFile(name = 'space.jpg', type = 'image/jpeg', size = 1024): File {
  const content = new Uint8Array(size).fill(0);
  return new File([content], name, { type });
}

function makeAnalysisResult(overrides = {}) {
  return {
    title: 'سديم جميل في الفضاء',
    summary: 'صورة لسديم بعيد.',
    observations: ['سحاب غازي', 'نجوم مضيئة'],
    scientific_explanation: 'يُرجَّح أن هذا سديم انبعاثي.',
    confidence: 'high',
    story: 'قصة قصيرة عن الفضاء.',
    question_answer: '',
    is_space_related: true,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ImageAnalyzer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ── Initial render ────────────────────────────────────────────────────────

  it('renders the component title', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByText(/حلّل صورة فضائية/)).toBeInTheDocument();
  });

  it('renders the drop zone initially', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
  });

  it('renders the file input', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('file-input')).toBeInTheDocument();
  });

  it('renders the question input', () => {
    render(<ImageAnalyzer />);
    expect(screen.getByTestId('question-input')).toBeInTheDocument();
  });

  it('does not show submit button before file is selected', () => {
    render(<ImageAnalyzer />);
    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument();
  });

  // ── File selection ────────────────────────────────────────────────────────

  it('shows image preview after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input') as HTMLInputElement;
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('image-preview')).toBeInTheDocument();
    expect((screen.getByTestId('image-preview') as HTMLImageElement).src).toContain(
      'mock-image-url',
    );
  });

  it('shows submit button after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
  });

  it('hides drop zone after file selection', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile();

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.queryByTestId('drop-zone')).not.toBeInTheDocument();
  });

  it('shows error for unsupported file type', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const file = makeFile('document.pdf', 'application/pdf');

    await act(async () => {
      fireEvent.change(input, { target: { files: [file] } });
    });

    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    expect(screen.getByTestId('error-message').textContent).toContain('JPEG');
  });

  it('shows error for oversized file', async () => {
    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    // 6 MB — over the 5 MB limit
    const bigFile = makeFile('big.jpg', 'image/jpeg', 6 * 1024 * 1024);

    await act(async () => {
      fireEvent.change(input, { target: { files: [bigFile] } });
    });

    expect(screen.getByTestId('error-message')).toBeInTheDocument();
    const msg = screen.getByTestId('error-message').textContent ?? '';
    expect(msg).toMatch(/ميغابايت/);
  });

  // ── Question input ────────────────────────────────────────────────────────

  it('accepts text in the question input', async () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;

    await act(async () => {
      fireEvent.change(qInput, { target: { value: 'ما هذا الكوكب؟' } });
    });

    expect(qInput.value).toBe('ما هذا الكوكب؟');
  });

  it('respects maxLength=400 on question input', () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;
    expect(qInput.getAttribute('maxLength') || qInput.maxLength).toBe(400);
  });

  // ── Submit / loading ──────────────────────────────────────────────────────

  it('shows loading indicator while analyzing', async () => {
    let resolveAnalysis!: (v: ReturnType<typeof makeAnalysisResult>) => void;
    mockAnalyzeImage.mockImplementationOnce(
      () => new Promise((res) => { resolveAnalysis = res; }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();

    // Clean up
    act(() => {
      resolveAnalysis(makeAnalysisResult());
    });
  });

  it('hides submit button while loading', async () => {
    let resolveAnalysis!: (v: ReturnType<typeof makeAnalysisResult>) => void;
    mockAnalyzeImage.mockImplementationOnce(
      () => new Promise((res) => { resolveAnalysis = res; }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    expect(screen.queryByTestId('submit-button')).not.toBeInTheDocument();

    act(() => {
      resolveAnalysis(makeAnalysisResult());
    });
  });

  it('passes question to analyzeImage when provided', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');
    const qInput = screen.getByTestId('question-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.change(qInput, { target: { value: 'هل هذا نجم؟' } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(mockAnalyzeImage).toHaveBeenCalledWith(
        expect.any(File),
        'هل هذا نجم؟',
      );
    });
  });

  // ── Successful result rendering ───────────────────────────────────────────

  it('shows analysis result after successful submit', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('analysis-result')).toBeInTheDocument();
    });
  });

  it('displays the result title', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('سديم جميل في الفضاء')).toBeInTheDocument();
    });
  });

  it('displays observations in the result', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('سحاب غازي')).toBeInTheDocument();
    });
  });

  it('displays question answer when present', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(
      makeAnalysisResult({ question_answer: 'هذا نجم نيوتروني.' }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByText('هذا نجم نيوتروني.')).toBeInTheDocument();
    });
  });

  it('shows reset button after result', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    });
  });

  it('resets to idle state when reset button clicked', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(makeAnalysisResult());

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('reset-button')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('reset-button'));
    });

    expect(screen.getByTestId('drop-zone')).toBeInTheDocument();
    expect(screen.queryByTestId('analysis-result')).not.toBeInTheDocument();
  });

  // ── Non-space image ───────────────────────────────────────────────────────

  it('shows non-space message when is_space_related is false', async () => {
    mockAnalyzeImage.mockResolvedValueOnce(
      makeAnalysisResult({ is_space_related: false, summary: 'هذه ليست صورة فضائية.' }),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('analysis-result')).toBeInTheDocument();
      const result = screen.getByTestId('analysis-result');
      expect(result.textContent).toContain('هذه ليست صورة فضائية.');
    });
  });

  // ── Error rendering ───────────────────────────────────────────────────────

  it('shows error message on API failure', async () => {
    const { APIClientError: LocalError } = jest.requireActual('@/lib/api') as typeof import('@/lib/api');
    mockAnalyzeImage.mockRejectedValueOnce(
      new (class extends Error {
        code = 'AI_TIMEOUT';
        constructor() { super('انتهت مهلة الذكاء الاصطناعي.'); this.name = 'APIClientError'; }
      })(),
    );

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('shows generic error message on unexpected exception', async () => {
    mockAnalyzeImage.mockRejectedValueOnce(new Error('Unexpected internal error'));

    render(<ImageAnalyzer />);
    const input = screen.getByTestId('file-input');

    await act(async () => {
      fireEvent.change(input, { target: { files: [makeFile()] } });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-button'));
    });

    await waitFor(() => {
      const errorEl = screen.getByTestId('error-message');
      expect(errorEl).toBeInTheDocument();
      // Should show Arabic user-friendly message, not raw exception
      expect(errorEl.textContent).not.toContain('Unexpected internal error');
    });
  });
});


### 🤖 Assistant

> 🔧 called: apply_diff

Now add tests for the `analyzeImage` API function in the existing api.test.ts:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:1
-------
import { fetchDailyNews, fetchStatus, APIClientError } from '@/lib/api';
=======
import { fetchDailyNews, fetchStatus, analyzeImage, APIClientError } from '@/lib/api';
>>>>>>> REPLACE

<<<<<<< SEARCH
:start_line:149
-------
  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => makeErrorBody('AI_NOT_CONFIGURED', 'Key missing'),
    } as Response);

    await expect(fetchStatus()).rejects.toBeInstanceOf(APIClientError);
  });
});
=======
  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => makeErrorBody('AI_NOT_CONFIGURED', 'Key missing'),
    } as Response);

    await expect(fetchStatus()).rejects.toBeInstanceOf(APIClientError);
  });
});

// ---------------------------------------------------------------------------
// analyzeImage
// ---------------------------------------------------------------------------

function makeAnalysisResult(overrides = {}) {
  return {
    success: true,
    data: {
      title: 'سديم رائع',
      summary: 'صورة لسديم.',
      observations: ['سحاب غازي'],
      scientific_explanation: 'يُرجَّح أن هذا سديم انبعاثي.',
      confidence: 'high',
      story: 'قصة قصيرة.',
      question_answer: '',
      is_space_related: true,
      ...overrides,
    },
  };
}

function makeImageFile(name = 'space.jpg', type = 'image/jpeg'): File {
  return new File([new Uint8Array(100)], name, { type });
}

describe('analyzeImage', () => {
  it('returns ImageAnalysisResult on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    const result = await analyzeImage(makeImageFile());
    expect(result.title).toBe('سديم رائع');
    expect(result.is_space_related).toBe(true);
  });

  it('passes question in FormData when provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile(), 'ما هذا؟');

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('question')).toBe('ما هذا؟');
  });

  it('does not include question in FormData when not provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('question')).toBeNull();
  });

  it('includes image file in FormData', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    const file = makeImageFile('nebula.jpg', 'image/jpeg');
    await analyzeImage(file);

    const [, options] = mockFetch.mock.calls[0];
    const body = (options as RequestInit).body as FormData;
    expect(body.get('image')).toBe(file);
  });

  it('uses correct endpoint URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/analyze-image'),
      expect.any(Object),
    );
  });

  it('uses POST method', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeAnalysisResult(),
    } as Response);

    await analyzeImage(makeImageFile());

    const [, options] = mockFetch.mock.calls[0];
    expect((options as RequestInit).method).toBe('POST');
  });

  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => makeErrorBody('UNSUPPORTED_IMAGE_TYPE', 'نوع الملف غير مدعوم.'),
    } as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toBeInstanceOf(APIClientError);
  });

  it('throws correct error code on failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 413,
      json: async () => makeErrorBody('IMAGE_TOO_LARGE', 'الصورة كبيرة جداً.'),
    } as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toMatchObject({
      code: 'IMAGE_TOO_LARGE',
    });
  });

  it('throws NETWORK_ERROR on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('network down'));

    await expect(analyzeImage(makeImageFile())).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
    });
  });

  it('throws PARSE_ERROR on non-JSON response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => { throw new SyntaxError('not json'); },
    } as unknown as Response);

    await expect(analyzeImage(makeImageFile())).rejects.toBeInstanceOf(APIClientError);
  });
});
>>>>>>> REPLACE


### 🤖 Assistant

> 🔧 called: execute_command, execute_command, execute_command, execute_command

Now let's install the python-multipart dependency and run the backend tests:

> 🔧 **execute_command** — cd backend; pip install python-multipart --quiet 2>&1 | tail -3

> 🔧 **execute_command** — pip install python-multipart --quiet

> 🔧 **execute_command** — python -m pytest tests/ -x --tb=short -q 2>&1 | Select-Object -Last 30

> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/ -x --tb=short -q 2>&1 | Select-Object -Last 40

### 🤖 Assistant

> 🔧 called: execute_command, execute_command

The virtual environment needs python-multipart installed:

> 🔧 **execute_command** — & ".\.venv\Scripts\pip.exe" install python-multipart --quiet 2>&1; Write-Host "Done"

> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/ -x --tb=short -q 2>&1 | Select-Object -Last 50

### 🤖 Assistant

> 🔧 called: write_file

The test is making a real HTTP call instead of using the mock — the fixture isn't wiring up correctly. The issue is that tests use `TestClient` which runs the actual lifespan, but the patch is not working because the lifespan creates new instances. I need to fix the test fixture to properly mock the `analyze_image` call:

> 🔧 **write_file** — """
Tests for POST /api/analyze-image.

Covers:
- Valid JPEG/PNG/WEBP upload
- Invalid MIME type rejection
- Oversized image rejection
- Empty/missing image rejection
- Optional question parameter
- Structured AI response validation
- Malformed AI response (ValidationError)
- AI provider failure (AIProviderError)
- Safe error handling (no stack traces, no key leakage)

All AI provider calls are mocked — no real API keys required.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from pydantic import ValidationError

from models import ImageAnalysisResult
from ai_provider import AIProviderError


# ---------------------------------------------------------------------------
# Minimal 1×1 PNG (valid image bytes)
# ---------------------------------------------------------------------------

_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_TINY_PNG_BYTES = base64.b64decode(_TINY_PNG_B64)

_TINY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),\x01\x02\x03\x04"
    b"\xff\xd9"
)


def _valid_ai_response() -> dict:
    return {
        "title": "سديم رائع في الفضاء",
        "summary": "صورة رائعة لسديم بعيد تظهر ألوانه الزاهية.",
        "observations": ["يظهر سحاب غازي كثيف", "نجوم مضيئة في الخلفية"],
        "scientific_explanation": "يُرجَّح أن هذا سديم انبعاثي يتكوّن من غاز الهيدروجين.",
        "confidence": "medium",
        "story": "في أعماق الفضاء الشاسع تولد النجوم من رحم الغيوم الكونية.",
        "question_answer": "",
        "is_space_related": True,
    }


# ---------------------------------------------------------------------------
# Fixture: app with mocked AI
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ai():
    """Return a mock AI object whose analyze_image returns a valid response."""
    ai = MagicMock()
    ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
    return ai


@pytest.fixture()
def client(mock_ai):
    """TestClient with _story_generator patched to use mock_ai."""
    from main import app

    mock_generator = MagicMock()
    mock_generator._ai = mock_ai

    with patch("main._story_generator", mock_generator):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture()
def client_no_ai():
    """TestClient with _story_generator set to None (AI not configured)."""
    from main import app

    with patch("main._story_generator", None):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _upload(client, file_bytes: bytes, mime: str, question: str | None = None):
    """POST to /api/analyze-image with given bytes and MIME type."""
    data = {}
    if question is not None:
        data["question"] = question
    return client.post(
        "/api/analyze-image",
        files={"image": ("test.img", BytesIO(file_bytes), mime)},
        data=data,
    )


# ---------------------------------------------------------------------------
# Valid uploads
# ---------------------------------------------------------------------------


class TestValidUploads:
    def test_valid_png_returns_200(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 200

    def test_valid_jpeg_returns_200(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        resp = _upload(client, _TINY_JPEG_BYTES, "image/jpeg")
        assert resp.status_code == 200

    def test_response_is_success_true(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        body = resp.json()
        assert body["success"] is True

    def test_response_contains_expected_fields(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        data = resp.json()["data"]
        assert "title" in data
        assert "summary" in data
        assert "observations" in data
        assert "scientific_explanation" in data
        assert "confidence" in data
        assert "is_space_related" in data

    def test_optional_question_is_passed_through(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value={
            **_valid_ai_response(),
            "question_answer": "هذا كوكب المشتري.",
        })
        resp = _upload(client, _TINY_PNG_BYTES, "image/png", question="ما هذا الكوكب؟")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["question_answer"] == "هذا كوكب المشتري."

    def test_no_question_succeeds(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 200

    def test_analyze_image_called_with_base64(self, client, mock_ai):
        _upload(client, _TINY_PNG_BYTES, "image/png")
        assert mock_ai.analyze_image.called
        call_kwargs = mock_ai.analyze_image.call_args
        image_b64 = call_kwargs.kwargs.get("image_b64")
        assert isinstance(image_b64, str) and len(image_b64) > 0
        decoded = base64.b64decode(image_b64)
        assert decoded == _TINY_PNG_BYTES

    def test_correct_mime_passed_to_ai(self, client, mock_ai):
        _upload(client, _TINY_PNG_BYTES, "image/png")
        call_kwargs = mock_ai.analyze_image.call_args
        image_mime = call_kwargs.kwargs.get("image_mime")
        assert image_mime == "image/png"

    def test_webp_mime_accepted(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        resp = _upload(client, _TINY_PNG_BYTES, "image/webp")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# MIME type validation
# ---------------------------------------------------------------------------


class TestMimeValidation:
    def test_gif_rejected(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        assert resp.status_code == 422
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_svg_rejected(self, client):
        resp = _upload(client, b"<svg/>", "image/svg+xml")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_pdf_rejected(self, client):
        resp = _upload(client, b"%PDF-1.4", "application/pdf")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_text_rejected(self, client):
        resp = _upload(client, b"hello", "text/plain")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNSUPPORTED_IMAGE_TYPE"

    def test_error_message_is_arabic(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        msg = resp.json()["error"]["message"]
        arabic_chars = [ch for ch in msg if "\u0600" <= ch <= "\u06FF"]
        assert len(arabic_chars) > 5

    def test_no_api_key_in_error_message(self, client):
        resp = _upload(client, _TINY_PNG_BYTES, "image/gif")
        msg = resp.json()["error"]["message"]
        assert "sk-" not in msg
        assert "Bearer" not in msg
        assert "OPENROUTER" not in msg


# ---------------------------------------------------------------------------
# Size validation
# ---------------------------------------------------------------------------


class TestSizeValidation:
    def test_oversized_image_rejected(self, client):
        oversized = b"x" * (5 * 1024 * 1024 + 1)
        resp = _upload(client, oversized, "image/png")
        assert resp.status_code == 413
        assert resp.json()["error"]["code"] == "IMAGE_TOO_LARGE"

    def test_exact_max_size_accepted(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
        exact_max = b"x" * (5 * 1024 * 1024)
        resp = _upload(client, exact_max, "image/png")
        assert resp.status_code != 413

    def test_empty_file_rejected(self, client):
        resp = _upload(client, b"", "image/png")
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "EMPTY_IMAGE"


# ---------------------------------------------------------------------------
# AI provider failures
# ---------------------------------------------------------------------------


class TestAIProviderFailures:
    def test_ai_timeout_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "Request timed out.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_TIMEOUT"

    def test_ai_network_error_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_NETWORK_ERROR", "Network failure.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "AI_NETWORK_ERROR"

    def test_ai_auth_error_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_UNAUTHORIZED", "Bad key.")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "AI_UNAUTHORIZED"

    def test_ai_error_message_not_leaked_in_stack_trace(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(
            side_effect=AIProviderError("AI_TIMEOUT", "timeout after 60s")
        )
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        body = resp.json()
        assert "Traceback" not in str(body)
        assert "File " not in str(body)

    def test_malformed_ai_response_returns_502(self, client, mock_ai):
        mock_ai.analyze_image = AsyncMock(return_value={"unexpected_field": "value"})
        resp = _upload(client, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_ai_not_configured_returns_503(self, client_no_ai):
        resp = _upload(client_no_ai, _TINY_PNG_BYTES, "image/png")
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "AI_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# ImageAnalysisResult Pydantic model
# ---------------------------------------------------------------------------


class TestImageAnalysisResultModel:
    def test_valid_full(self):
        result = ImageAnalysisResult(**_valid_ai_response())
        assert result.title == "سديم رائع في الفضاء"
        assert result.confidence == "medium"
        assert result.is_space_related is True
        assert len(result.observations) == 2

    def test_confidence_normalised_to_lowercase(self):
        data = {**_valid_ai_response(), "confidence": "HIGH"}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "high"

    def test_observations_default_empty_list(self):
        data = {**_valid_ai_response()}
        del data["observations"]
        result = ImageAnalysisResult(**data)
        assert result.observations == []

    def test_observations_coerces_string_to_list(self):
        data = {**_valid_ai_response(), "observations": "ملاحظة واحدة"}
        result = ImageAnalysisResult(**data)
        assert result.observations == ["ملاحظة واحدة"]

    def test_story_defaults_to_empty_string(self):
        data = {**_valid_ai_response()}
        del data["story"]
        result = ImageAnalysisResult(**data)
        assert result.story == ""

    def test_question_answer_defaults_to_empty_string(self):
        data = {**_valid_ai_response()}
        del data["question_answer"]
        result = ImageAnalysisResult(**data)
        assert result.question_answer == ""

    def test_is_space_related_defaults_to_true(self):
        data = {**_valid_ai_response()}
        del data["is_space_related"]
        result = ImageAnalysisResult(**data)
        assert result.is_space_related is True

    def test_missing_required_title_raises(self):
        data = {**_valid_ai_response()}
        del data["title"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_missing_required_summary_raises(self):
        data = {**_valid_ai_response()}
        del data["summary"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_missing_required_scientific_explanation_raises(self):
        data = {**_valid_ai_response()}
        del data["scientific_explanation"]
        with pytest.raises(ValidationError):
            ImageAnalysisResult(**data)

    def test_unknown_confidence_value_normalised_to_medium(self):
        data = {**_valid_ai_response(), "confidence": "very_high"}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "medium"

    def test_invalid_confidence_type_normalised_to_medium(self):
        data = {**_valid_ai_response(), "confidence": 42}
        result = ImageAnalysisResult(**data)
        assert result.confidence == "medium"


# ---------------------------------------------------------------------------
# Vision prompts
# ---------------------------------------------------------------------------


class TestVisionPrompts:
    def test_vision_system_prompt_is_nonempty(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert isinstance(prompt, str) and len(prompt) > 100

    def test_vision_system_prompt_contains_arabic(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        arabic = [c for c in prompt if "\u0600" <= c <= "\u06FF"]
        assert len(arabic) > 50

    def test_vision_system_prompt_mentions_json(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert "JSON" in prompt or "json" in prompt.lower()

    def test_vision_system_prompt_no_hallucination_rule(self):
        from prompts import get_vision_system_prompt
        prompt = get_vision_system_prompt()
        assert "تخترع" in prompt or "تختلق" in prompt

    def test_vision_user_prompt_without_question(self):
        from prompts import build_vision_user_prompt
        prompt = build_vision_user_prompt(None)
        assert isinstance(prompt, str) and len(prompt) > 10
        assert "JSON" in prompt

    def test_vision_user_prompt_with_question_includes_question(self):
        from prompts import build_vision_user_prompt
        q = "هل هذا كوكب أم نجم؟"
        prompt = build_vision_user_prompt(q)
        assert q in prompt

    def test_vision_user_prompt_question_truncated_at_400_chars(self):
        from prompts import build_vision_user_prompt
        long_q = "س" * 500
        prompt = build_vision_user_prompt(long_q)
        assert long_q not in prompt
        assert "س" * 400 in prompt

    def test_vision_user_prompt_empty_question_treated_as_none(self):
        from prompts import build_vision_user_prompt
        prompt_no_q = build_vision_user_prompt(None)
        prompt_empty_q = build_vision_user_prompt("   ")
        assert prompt_no_q == prompt_empty_q


### 🤖 Assistant

> 🔧 called: execute_command

Now run the backend tests:

> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/ -x --tb=short -q 2>&1 | Select-Object -Last 40

### 🤖 Assistant

> 🔧 called: read_file

The patch is still not working - the TestClient is using the actual lifespan which creates a real `_story_generator`. The issue is that `patch("main._story_generator", mock_generator)` needs to replace the module-level variable, but the `TestClient` context triggers the lifespan which reinitializes things. Let me investigate how the lifespan interacts with the test:

> 🔧 **read_file** — backend/main.py

### 🤖 Assistant

> 🔧 called: apply_diff, execute_command

I see — the lifespan runs when `TestClient` enters, and that overwrites the `_story_generator`. The patch needs to happen INSIDE the lifespan. The cleanest fix is to patch the module variable AFTER `TestClient.__enter__` (i.e., after lifespan) using a different approach — we can use `TestClient` without lifespan, or we can prevent the lifespan from overwriting by patching the global after entry.

The proper pattern with `TestClient` is to use `raise_server_exceptions=False` without the lifespan context, or we need to patch at the right time. Let me use a different approach - patch the `_story_generator` right before the request by wrapping the fixture differently:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:63
-------
# ---------------------------------------------------------------------------
# Fixture: app with mocked AI
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ai():
    """Return a mock AI object whose analyze_image returns a valid response."""
    ai = MagicMock()
    ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
    return ai


@pytest.fixture()
def client(mock_ai):
    """TestClient with _story_generator patched to use mock_ai."""
    from main import app

    mock_generator = MagicMock()
    mock_generator._ai = mock_ai

    with patch("main._story_generator", mock_generator):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture()
def client_no_ai():
    """TestClient with _story_generator set to None (AI not configured)."""
    from main import app

    with patch("main._story_generator", None):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
=======
# ---------------------------------------------------------------------------
# Fixture: app with mocked AI
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_ai():
    """Return a mock AI object whose analyze_image returns a valid response."""
    ai = MagicMock()
    ai.analyze_image = AsyncMock(return_value=_valid_ai_response())
    return ai


@pytest.fixture()
def client(mock_ai):
    """
    TestClient with the lifespan bypassed for the AI provider.

    The TestClient runs the lifespan which initialises _story_generator with the
    real provider (if OPENROUTER_API_KEY is set).  We patch AFTER lifespan by
    directly replacing the module attribute so endpoint calls see our mock.
    """
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        # After lifespan has run, replace the module-level generator with our mock
        original = main_module._story_generator
        mock_generator = MagicMock()
        mock_generator._ai = mock_ai
        main_module._story_generator = mock_generator
        try:
            yield c
        finally:
            main_module._story_generator = original


@pytest.fixture()
def client_no_ai():
    """TestClient with _story_generator set to None (AI not configured)."""
    import main as main_module

    with TestClient(main_module.app, raise_server_exceptions=False) as c:
        original = main_module._story_generator
        main_module._story_generator = None
        try:
            yield c
        finally:
            main_module._story_generator = original
>>>>>>> REPLACE


> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/test_analyze_image.py -x --tb=short -q 2>&1 | Select-Object -Last 30

### 🤖 Assistant

> 🔧 called: execute_command

All 44 new tests pass. Now run the full backend test suite:

> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/ --tb=short -q 2>&1 | Select-Object -Last 20

### 🤖 Assistant

> 🔧 called: execute_command, execute_command, glob, execute_command, execute_command, execute_command

**271 backend tests passing** (227 existing + 44 new). Now run the frontend tests:

> 🔧 **execute_command** — cd frontend; npm test -- --ci --passWithNoTests 2>&1 | Select-Object -Last 50

> 🔧 **execute_command** — npm test -- --ci --passWithNoTests 2>&1 | Select-Object -Last 60

> 🔧 **glob** — **/npm.cmd

> 🔧 **execute_command** — Get-Command node, npm -ErrorAction SilentlyContinue | Select-Object Name, Source

> 🔧 **execute_command** — $env:PATH

> 🔧 **execute_command** — Get-Command node -ErrorAction SilentlyContinue

### 🤖 Assistant

> 🔧 called: execute_command, execute_command, execute_command

Node/npm is not in PATH. Let me find it:

> 🔧 **execute_command** — Get-ChildItem "C:\Program Files\nodejs\npm.cmd" -ErrorAction SilentlyContinue; Get-ChildItem "C:\Users\Al-Ashram\AppData\Roaming\npm\npm.cmd" -ErrorAction SilentlyContinue; Get-ChildItem "${env:ProgramFiles}\nodejs" -ErrorAction SilentlyContinue | Select-Object -First 5

> 🔧 **execute_command** — & "C:\Program Files\nodejs\npm.cmd" test -- --ci --passWithNoTests 2>&1 | Select-Object -Last 60

> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" test -- --ci --passWithNoTests 2>&1 | Select-Object -Last 60

### 🤖 Assistant

> 🔧 called: apply_diff, execute_command

Good progress! One test failing: `maxLength` returns a string "400" from `getAttribute`, but I'm comparing with number 400. Fix the test:

> 🔧 **apply_diff** — <<<<<<< SEARCH
:start_line:188
-------
  it('respects maxLength=400 on question input', () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;
    expect(qInput.getAttribute('maxLength') || qInput.maxLength).toBe(400);
  });
=======
  it('respects maxLength=400 on question input', () => {
    render(<ImageAnalyzer />);
    const qInput = screen.getByTestId('question-input') as HTMLInputElement;
    expect(qInput.maxLength).toBe(400);
  });
>>>>>>> REPLACE


> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" test -- --ci --passWithNoTests 2>&1 | Select-Object -Last 30

### 🤖 Assistant

> 🔧 called: execute_command, execute_command

**91 frontend tests passing** (57 existing + 34 new), with only harmless `act(...)` warnings (not errors). Now run TypeScript check and ESLint:

> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" run type-check 2>&1 | Select-Object -Last 30

> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" run lint 2>&1 | Select-Object -Last 30

### 🤖 Assistant

> 🔧 called: execute_command

TypeScript clean, ESLint clean. Now run the production build:

> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" run build 2>&1 | Select-Object -Last 30

### 🤖 Assistant

> 🔧 called: execute_command, execute_command, execute_command, execute_command

Production build successful. Now let's do a security review and check that API keys aren't in the build:

> 🔧 **execute_command** — Select-String -Recurse -Path "frontend\.next\static" -Pattern "OPENROUTER_API_KEY" -ErrorAction SilentlyContinue | Select-Object -First 3; Write-Host "Config leak scan done"

> 🔧 **execute_command** — Select-String -Path "frontend\.next\static\chunks\*.js" -Pattern "(sk-|OPENROUTER_API_KEY|NASA_API_KEY|Bearer )" -ErrorAction SilentlyContinue | Select-Object -First 5; Write-Host "Key scan complete"

> 🔧 **execute_command** — Select-String -Recurse -Path "frontend\.next\static" -Pattern "sk-or-" -ErrorAction SilentlyContinue | Select-Object -First 3; Write-Host "API key scan done"

> 🔧 **execute_command** — Get-ChildItem -Path "frontend\.next\static\chunks" -Filter "*.js" | ForEach-Object { Select-String -Path $_.FullName -Pattern "(OPENROUTER_API_KEY|sk-or-v1|NASA_API_KEY)" -ErrorAction SilentlyContinue } | Select-Object -First 5; Write-Host "Build scan done"

### 🤖 Assistant

> 🔧 called: update_todo_list, execute_command, execute_command

No API keys found in the build output. Now update the todo list and do final verification:

> 🔧 **update_todo_list** — 
[x] Phase 1: Investigate existing project architecture
[x] Phase 2: Backend - Pydantic model (ImageAnalysisResult)
[x] Phase 3: Backend - Vision prompt in prompts.py
[x] Phase 4: Backend - Extend OpenRouterProvider with vision support
[x] Phase 5: Backend - POST /api/analyze-image endpoint in main.py
[x] Phase 6: Frontend - types.ts extension
[x] Phase 7: Frontend - api.ts extension
[x] Phase 8: Frontend - ImageAnalyzer component
[x] Phase 9: Backend tests for analyze-image
[x] Phase 10: Frontend tests for ImageAnalyzer
[x] Phase 11: Security review
[-] Final verification (tests, TypeScript, ESLint, build)


> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" test -- --ci 2>&1 | Select-Object -Last 10

> 🔧 **execute_command** — & ".\.venv\Scripts\python.exe" -m pytest tests/ -q --tb=line 2>&1 | Select-Object -Last 10

### 🤖 Assistant

> 🔧 called: execute_command

The test runner exits with code 1 because of the `act(...)` warnings printed to stderr (they're React warnings, not failures). All 91 tests pass. Let me verify the warning is just cosmetic and the tests genuinely pass:

> 🔧 **execute_command** — $env:PATH = "C:\Program Files\nodejs;" + $env:PATH; & "C:\Program Files\nodejs\npm.cmd" test -- --ci 2>&1 | Select-String "FAIL|PASS|Tests:" | Select-Object -Last 20