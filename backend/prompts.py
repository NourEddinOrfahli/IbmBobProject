"""
Prompt engineering for Space Interpreter.

All prompt construction lives here so that:
- Prompts are easy to read, test, and iterate on independently of business logic.
- The system prompt embeds strong scientific-accuracy rules.
- Output size is deliberately constrained so free-tier models do not truncate.
"""

from __future__ import annotations

from typing import Optional

from models import NASAAPODData, NASADONKIEvent


# ---------------------------------------------------------------------------
# System prompt — persona + strict rules + concise output spec
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
أنت مُفسِّر علمي متخصص في علم الفلك واستكشاف الفضاء.
مهمتك: تحويل بيانات ناسا إلى تقرير علمي موجز بالعربية الفصحى.

القواعد الصارمة:
1. لا تخترع حقائق — استند فقط إلى البيانات المُقدَّمة.
2. فرّق بين الحقائق الرسمية والتفسيرات.
3. لا تملأ الفراغات بتخمينات — إذا لم تتوفر معلومة، اذكر ذلك صراحةً.
4. اعطِ الأولوية للدقة العلمية.
5. يجب أن تكون جميع قيم الحقول النصية (title, summary, scientific_explanation, key_facts, why_it_matters, story) مكتوبة بالعربية الفصحى المعاصرة حصراً. لا تكتب أي جملة بالإنجليزية أو أي لغة أخرى.
6. أعِد JSON صحيحاً فقط — لا نصوص خارجه ولا علامات Markdown.

تحذير لغوي صارم: إذا كتبت أي حقل نصي بالإنجليزية فإن الإجابة ستُرفض تلقائياً.
يجب أن تحتوي كل جملة في title وsummary وscientific_explanation وkey_facts وwhy_it_matters وstory على كلمات عربية فقط.

هيكل الإخراج (JSON object فقط، لا شيء قبله أو بعده):
{
  "title": "عنوان قصير (10 كلمات كحد أقصى)",
  "summary": "جملتان إلى ثلاث جمل",
  "scientific_explanation": "ثلاث إلى خمس جمل علمية دقيقة",
  "key_facts": ["حقيقة موجزة 1", "حقيقة موجزة 2", "حقيقة موجزة 3"],
  "why_it_matters": "جملتان إلى ثلاث جمل",
  "story": "قصة جذابة من 100 إلى 150 كلمة عربية فقط",
  "source_data": {"source": "NASA APOD", "date": "YYYY-MM-DD", "title": "..."},
  "confidence": "high",
  "language": "ar"
}

تحذير: يجب أن يكون الإخراج كائن JSON كاملاً وصحيحاً. لا تبدأ بنص ولا تُضِف تعليقاً.
"""

# Retry system prompt — format rules only, no NASA data (data lives in user message)
RETRY_SYSTEM_PROMPT = """\
أعِد الإجابة بصيغة JSON صحيحة فقط. لا تضمّن أي نص أو Markdown خارج كائن JSON.
اجعل كل حقل موجزاً لتجنب الاقتطاع. الإخراج يجب أن يكون كائن JSON واحداً مكتملاً.
جميع الحقول النصية (title, summary, scientific_explanation, key_facts, why_it_matters, story) يجب أن تكون بالعربية الفصحى المعاصرة حصراً. لا تستخدم الإنجليزية.
"""

# Retry instruction appended AFTER the original NASA user prompt — never sent alone.
_RETRY_INSTRUCTIONS = """\

تعذّر تنسيق الإجابة السابقة.
أعِد إنشاء الإجابة اعتماداً حصراً على بيانات NASA الموجودة أعلاه.
لا تغيّر الموضوع ولا تستبدل بيانات NASA بأي معلومات أخرى.
أخرِج كائن JSON واحداً صحيحاً ومكتملاً فقط.

تحذير لغوي: يجب أن تكون جميع الحقول النصية (title, summary, scientific_explanation, key_facts, why_it_matters, story) بالعربية الفصحى المعاصرة حصراً. الإجابة بالإنجليزية مرفوضة.

اجعل الحقول مختصرة:
- title: 5-8 كلمات عربية
- summary: جملتان عربيتان
- scientific_explanation: 3 جمل قصيرة عربية
- key_facts: 3 حقائق قصيرة عربية
- why_it_matters: جملتان عربيتان
- story: 80-100 كلمة عربية

ممنوع اختراع مصدر أو موضوع غير موجود في بيانات NASA أعلاه.
"""


# ---------------------------------------------------------------------------
# User-prompt builders
# ---------------------------------------------------------------------------


def build_apod_prompt(apod: NASAAPODData) -> str:
    """
    Build a user-role prompt from a normalised APOD payload.

    Only includes fields that are actually present.
    The NASA explanation is truncated to 800 characters to prevent
    the input itself from consuming too many tokens.
    """
    # Truncate the explanation to avoid bloating the prompt on its own
    explanation = apod.explanation
    if len(explanation) > 800:
        explanation = explanation[:800].rstrip() + "…"

    lines: list[str] = [
        "بيانات ناسا — صورة الفلك اليومية (APOD):",
        "",
        f"العنوان: {apod.title}",
        f"التاريخ: {apod.date}",
        f"نوع الوسائط: {apod.media_type}",
        "",
        "الوصف الرسمي:",
        explanation,
    ]

    if apod.copyright:
        lines.append(f"حقوق النشر: {apod.copyright}")

    lines += [
        "",
        "أعِد الإجابة بصيغة JSON فقط وفق الهيكل المُحدَّد.",
    ]

    return "\n".join(lines)


def build_apod_with_donki_prompt(
    apod: NASAAPODData,
    donki_events: list[NASADONKIEvent],
) -> str:
    """
    Build a prompt that includes DONKI events alongside APOD data.
    Caps DONKI events at 3 (reduced from 5) to save tokens.
    """
    base = build_apod_prompt(apod)

    if not donki_events:
        return base

    event_lines: list[str] = ["", "أحداث طقس الفضاء الأخيرة (DONKI):"]
    for i, evt in enumerate(donki_events[:3], start=1):  # cap at 3 to save tokens
        event_lines.append(f"الحدث {i}: {evt.event_type}")
        if evt.begin_time:
            event_lines.append(f"  وقت البدء: {evt.begin_time}")

    combined = base + "\n" + "\n".join(event_lines) + "\n"
    return combined


def build_custom_context_prompt(context: str) -> str:
    """
    Build a prompt from free-text context supplied by the caller.
    Context is truncated to 800 characters to keep the prompt manageable.
    """
    if len(context) > 800:
        context = context[:800].rstrip() + "…"

    return (
        "السياق الفضائي:\n\n"
        f"{context}\n\n"
        "أعِد الإجابة بصيغة JSON فقط وفق الهيكل المُحدَّد. لا نصوص خارج JSON."
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def get_system_prompt() -> str:
    """Return the system prompt. Exposed as a function for testability."""
    return SYSTEM_PROMPT


def build_retry_user_prompt(original_user_prompt: str) -> str:
    """
    Build the retry user message by re-embedding the complete original NASA
    user prompt followed by concise retry instructions.

    The original_user_prompt is preserved verbatim so the model is grounded
    in exactly the same NASA APOD data as the first attempt.  The retry
    instructions are appended after — never sent without the NASA context.
    """
    return original_user_prompt + _RETRY_INSTRUCTIONS


def get_retry_prompts() -> tuple[str, str]:
    """
    Kept for backward compatibility with existing tests that do not exercise
    the grounding path.  Returns the system prompt and the bare instructions
    string — callers that need grounding must use build_retry_user_prompt().
    """
    return RETRY_SYSTEM_PROMPT, _RETRY_INSTRUCTIONS


# ---------------------------------------------------------------------------
# Vision system prompt — image analysis persona + strict rules
# ---------------------------------------------------------------------------

VISION_SYSTEM_PROMPT = """\
أنت "مترجم الفضاء" — مُفسِّر علمي عربي متخصص في تحليل صور الفضاء.
مهمتك: مساعدة المستخدمين العاديين على فهم صور الفضاء بدقة علمية وباللغة العربية الفصحى.

القواعد الصارمة:
1. حلِّل فقط ما تراه فعلاً في الصورة — لا تخترع أو تفترض.
2. لا تختلق حقائق علمية أو أرقاماً أو قياسات أو أسماء مهمات ناسا.
3. فرِّق بوضوح بين الملاحظة (ما تراه) والتفسير (ما يُرجَّح علمياً).
4. أعبِّر صراحةً عن الغموض — قل "يُحتمل" أو "يبدو أنه" عند الشك.
5. أجب على سؤال المستخدم مباشرةً إذا كان موجوداً.
6. استخدم عربية فصحى واضحة وميسّرة.
7. لا تدّعي تحقق ناسا ما لم تكن بيانات ناسا متاحة فعلاً.
8. إذا لم تكن الصورة ذات صلة بالفضاء، قل ذلك بدلاً من فرض تفسير فضائي.
9. لا تكشف أي تفكير داخلي أو استنتاجات مخفية — أعطِ النتيجة النهائية فقط.
10. جميع الحقول النصية يجب أن تكون بالعربية الفصحى حصراً.

هيكل الإخراج (JSON object فقط، لا شيء قبله أو بعده):
{
  "title": "عنوان وصفي قصير للصورة (8 كلمات كحد أقصى)",
  "summary": "جملتان إلى ثلاث جمل تصف الصورة عموماً",
  "observations": [
    "ملاحظة بصرية 1 — ما تراه فعلاً",
    "ملاحظة بصرية 2",
    "ملاحظة بصرية 3"
  ],
  "scientific_explanation": "تفسير علمي في ثلاث إلى أربع جمل، مع التمييز الواضح بين الحقائق والاحتمالات",
  "confidence": "high|medium|low",
  "story": "قصة عربية قصيرة من 60 إلى 80 كلمة مستوحاة من الصورة (اتركها فارغة إذا لم تكن مناسبة)",
  "question_answer": "إجابة مباشرة على سؤال المستخدم (اتركها فارغة إذا لم يُطرح سؤال)",
  "is_space_related": true
}

تحذير: أعِد JSON صحيحاً فقط. لا نصوص خارجه. لا Markdown.
"""


def build_vision_user_prompt(question: Optional[str] = None) -> str:
    """
    Build the user-role text message to accompany the image in a vision request.

    The image itself is passed separately as base64 in the multimodal content.
    This function returns only the text part.
    """
    if question and question.strip():
        # Truncate to 400 characters to prevent prompt injection
        safe_q = question.strip()[:400]
        return (
            f"يرجى تحليل هذه الصورة الفضائية بدقة علمية.\n\n"
            f"سؤال المستخدم: {safe_q}\n\n"
            "أعِد JSON صحيحاً فقط وفق الهيكل المُحدَّد. لا نصوص خارج JSON."
        )
    return (
        "يرجى تحليل هذه الصورة الفضائية بدقة علمية.\n\n"
        "أعِد JSON صحيحاً فقط وفق الهيكل المُحدَّد. لا نصوص خارج JSON."
    )


def get_vision_system_prompt() -> str:
    """Return the vision system prompt. Exposed as a function for testability."""
    return VISION_SYSTEM_PROMPT


def build_prompt_for_apod(
    apod: NASAAPODData,
    donki_events: list[NASADONKIEvent] | None = None,
) -> tuple[str, str]:
    """
    Convenience wrapper that returns ``(system_prompt, user_prompt)`` ready
    to pass to ``AIProvider.generate_structured_response``.
    """
    system = get_system_prompt()
    if donki_events:
        user = build_apod_with_donki_prompt(apod, donki_events)
    else:
        user = build_apod_prompt(apod)
    return system, user
