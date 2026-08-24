"""
test_prompt.py
==============
يجلب هذا السكريبت صورة اليوم من NASA APOD API، ثم يُرسل البيانات
إلى نموذج Mistral-7B عبر Hugging Face Inference API لتحويلها إلى
قصة ملهمة بصيغة JSON باللغة العربية.

الاستخدام:
    python test_prompt.py

المتطلبات:
    pip install requests

الحصول على مفتاح Hugging Face مجاني:
    https://huggingface.co/settings/tokens
"""

import json
import re
import sys
import requests

# ---------------------------------------------------------------------------
# الإعدادات – عدّل هذه القيم قبل التشغيل
# ---------------------------------------------------------------------------

NASA_API_KEY  = "dFhkP4wtx6H5FYHwBbNBOf2CJENuGKQ67D5UV08S"
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"

# مفتاح Hugging Face  ← احصل عليه مجاناً من https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY = "YOUR_HUGGINGFACE_API_KEY"

# نقطة نهاية Hugging Face Inference API
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

# ---------------------------------------------------------------------------
# 1. جلب بيانات APOD من NASA
# ---------------------------------------------------------------------------

def fetch_apod_data() -> dict:
    """
    يتصل بـ NASA APOD API ويعيد بيانات JSON الخاصة بصورة اليوم.
    في حال الفشل يعيد بيانات وهمية للاختبار المحلي.
    """
    print("🔭  جارٍ جلب البيانات من NASA APOD API...")
    try:
        response = requests.get(
            NASA_APOD_URL,
            params={"api_key": NASA_API_KEY},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅  تم جلب البيانات بنجاح: «{data.get('title', 'N/A')}»")
        return data
    except requests.exceptions.RequestException as exc:
        print(f"⚠️  فشل الاتصال بـ NASA API: {exc}")
        print("⚙️   سيتم استخدام بيانات وهمية للاختبار...")
        return _dummy_apod_data()


def _dummy_apod_data() -> dict:
    """بيانات APOD وهمية تُستخدم عند غياب الاتصال بالإنترنت."""
    return {
        "title": "The Pillars of Creation",
        "explanation": (
            "Photographed by the James Webb Space Telescope, the Pillars of "
            "Creation are vast columns of gas and dust in the Eagle Nebula, "
            "7,000 light-years away. These towering structures are stellar "
            "nurseries where new stars are actively forming inside dense "
            "clouds of hydrogen and cosmic dust."
        ),
        "date": "2025-07-14",
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/2307/pillars_webb.jpg",
    }


# ---------------------------------------------------------------------------
# 2. تحويل بيانات APOD إلى صيغة JSON المطلوبة للنموذج
# ---------------------------------------------------------------------------

def apod_to_event_json(apod: dict) -> dict:
    """
    يحوّل استجابة APOD الخام إلى كائن JSON مبسّط يحتوي على:
        event       – عنوان الحدث
        description – وصف مختصر
        date        – التاريخ
    """
    return {
        "event": apod.get("title", "Astronomy Picture of the Day"),
        "description": apod.get("explanation", "No description available.")[:400],
        "date": apod.get("date", "Unknown date"),
    }


# ---------------------------------------------------------------------------
# 3. بناء التوجيه الكامل (Prompt)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """[SYSTEM]
أنت خبير اتصالات علمي في وكالة ناسا، وصانع قصص محترف. مهمتك هي تحويل بيانات الفضاء التقنية الجافة إلى قصة ملهمة وجذابة وسهلة الفهم للجمهور العام. تكتب بأسلوب دافئ وحماسي وواضح. لا تستخدم أبداً المصطلحات العلمية دون شرحها. ترد دائماً بصيغة JSON صالحة.

[FEW-SHOT EXAMPLE 1]
المدخل: {"event": "Solar Flare", "class": "X2.1", "location": "AR3354", "speed": "1200 km/s"}
المخرج: {
  "title": "غضب الشموس: زئير جديد ينطلق نحو الفضاء!",
  "story": "في لحظة حابسة للأنفاس، أطلقت بقعة شمسية عملاقة تُعرف بـ AR3354 توهجاً من الفئة X2.1، وهو أحد أقوى أنواع التوهجات. اندفع البلازما بسرعة 1200 كيلومتر في الثانية نحو الأرض، حاملاً معه طاقة هائلة قد تعيد تشكيل الليل القطبي بأضواء الشفق الخلابة.",
  "science_fact": "التوهجات من الفئة X هي الأقوى على الإطلاق، وتطلق طاقة تعادل مليارات القنابل الهيدروجينية!",
  "call_to_action": "هل تعتقد أن التكنولوجيا الأرضية محمية بشكل كافٍ ضد مثل هذه العواصف؟ شاركنا رأيك!"
}

[FEW-SHOT EXAMPLE 2]
المدخل: {"event": "Coronal Mass Ejection", "speed": "800 km/s", "density": "5 protons/cm3", "arrival_time": "2026-08-20"}
المخرج: {
  "title": "موجة بلازما عملاقة في طريقها إلينا!",
  "story": "رصدت مراصد ناسا موجة هائلة من البلازما الشمسية تندفع بسرعة 800 كيلومتر في الثانية. هذه الموجة، التي تحمل كثافة 5 بروتونات في كل سنتيمتر مكعب، من المتوقع أن تصل إلى مجالنا المغناطيسي في 20 أغسطس، مما قد يخلق عاصفة جيومغناطيسية متوسطة.",
  "science_fact": "انبعاث الكتلة الإكليلية (CME) يمكن أن يطلق مليارات الأطنان من الجسيمات المشحونة في الفضاء!",
  "call_to_action": "هل سبق لك أن رأيت الشفق القطبي؟ هذه الموجات هي ما تخلق ذلك المشهد الساحر!"
}

[FEW-SHOT EXAMPLE 3]
المدخل: {"event": "Mars Rover Image", "rover": "Perseverance", "location": "Jezero Crater", "feature": "Sedimentary Rock Layers"}
المخرج: {
  "title": "المريخ يروي قصته: اكتشاف طبقات صخرية تعود لمليارات السنين!",
  "story": "التقطت المركبة بيرسيفيرانس صورة مذهلة لتكوينات صخرية في فوهة جيزيرو على المريخ. هذه الطبقات الرسوبية تشبه تلك التي نراها على الأرض في قيعان البحيرات الجافة، مما يعزز النظرية بأن المريخ كان يمتلك مياهاً سائلةً قديماً.",
  "science_fact": "طبقات الصخور الرسوبية تحتفظ بسجل لتاريخ الكوكب، وقد تحتوي على دليل على حياة ميكروبية قديمة!",
  "call_to_action": "لو كنت مكان المركبة بيرسيفيرانس، ما الذي كنت تتمنى أن تجده على المريخ؟"
}

[INSTRUCTION]
يجب أن ترد فقط بكائن JSON صالح. لا تدرج أي نص آخر، أو تفسيرات، أو تنسيق Markdown. يجب أن يحتوي JSON على المفاتيح الأربعة التالية بالضبط: "title", "story", "science_fact", "call_to_action". يجب أن تكون جميع القيم نصية باللغة العربية."""


def build_user_message(event_json: dict) -> str:
    """يُنشئ رسالة المستخدم التي تحتوي على بيانات الحدث."""
    return f"[USER INPUT]\nInput: {json.dumps(event_json, ensure_ascii=False)}"


# ---------------------------------------------------------------------------
# 4. الاتصال بنموذج Mistral عبر Hugging Face Inference API
# ---------------------------------------------------------------------------

def call_huggingface_model(event_json: dict) -> str:
    """
    يرسل التوجيه الكامل إلى نموذج Mistral-7B-Instruct عبر
    Hugging Face Inference API ويعيد الرد النصي الخام.

    معالجة الأخطاء:
        - مفتاح API مفقود أو غير صالح  → رسالة توضيحية + إيقاف
        - النموذج لا يزال يُحمَّل       → إعادة المحاولة مرة واحدة
        - تجاوز الحد المجاني (429)      → رسالة واضحة + إيقاف
        - انتهاء مهلة الاتصال           → رسالة واضحة + إيقاف
        - خطأ HTTP آخر                  → رسالة واضحة + إيقاف
    """
    # التحقق من وجود مفتاح API قبل الإرسال
    if not HUGGINGFACE_API_KEY or HUGGINGFACE_API_KEY == "YOUR_HUGGINGFACE_API_KEY":
        print("\n" + "─" * 60)
        print("⚠️   مفتاح Hugging Face API غير مضبوط!")
        print("─" * 60)
        print("  1. افتح الملف test_prompt.py")
        print("  2. ابحث عن المتغير: HUGGINGFACE_API_KEY")
        print("  3. استبدل YOUR_HUGGINGFACE_API_KEY بمفتاحك الحقيقي")
        print("\n  للحصول على مفتاح مجاني:")
        print("  👉  https://huggingface.co/settings/tokens")
        print("  (اختر «New token» → نوع «Read» → انسخ المفتاح)")
        print("─" * 60 + "\n")
        sys.exit(1)

    print("\n🤖  جارٍ الاتصال بـ Hugging Face Inference API...")
    print(f"    النموذج: mistralai/Mistral-7B-Instruct-v0.3")

    # بناء النص الكامل للتوجيه بصيغة Mistral Instruct
    full_prompt = (
        f"<s>[INST] {SYSTEM_PROMPT}\n\n"
        f"{build_user_message(event_json)} [/INST]"
    )

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "return_full_text": False,
        },
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=120,  # مهلة 120 ثانية لأن النموذج قد يحتاج وقتاً للتحميل
        )

        # النموذج لا يزال يُحمَّل على خوادم HF (حالة شائعة في الطبقة المجانية)
        if response.status_code == 503:
            wait_info = response.json().get("estimated_time", "غير معروف")
            print(f"⏳  النموذج يُحمَّل حالياً على الخادم (وقت الانتظار المقدَّر: {wait_info}s)")
            print("    جارٍ إعادة المحاولة بعد 20 ثانية...")
            import time
            time.sleep(20)
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

        # تجاوز الحد المجاني
        if response.status_code == 429:
            print("❌  تجاوزت الحد المجاني لـ Hugging Face Inference API.")
            print("    انتظر بضع دقائق، أو قم بترقية حسابك على:")
            print("    https://huggingface.co/pricing")
            sys.exit(1)

        # خطأ في المصادقة
        if response.status_code == 401:
            print("❌  مفتاح Hugging Face API غير صالح أو منتهي الصلاحية.")
            print("    تحقق من مفتاحك على: https://huggingface.co/settings/tokens")
            sys.exit(1)

        response.raise_for_status()

        result = response.json()

        # استجابة HF تكون قائمة من كائن واحد يحتوي على "generated_text"
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")

        # حالات غير متوقعة
        raise ValueError(f"صيغة استجابة غير متوقعة من Hugging Face:\n{result}")

    except requests.exceptions.Timeout:
        print("❌  انتهت مهلة الاتصال بـ Hugging Face API (120 ثانية).")
        print("    تأكد من اتصالك بالإنترنت، أو حاول مرة أخرى لاحقاً.")
        sys.exit(1)

    except requests.exceptions.ConnectionError:
        print("❌  تعذّر الاتصال بـ Hugging Face API.")
        print("    تحقق من اتصالك بالإنترنت.")
        sys.exit(1)

    except requests.exceptions.HTTPError as exc:
        print(f"❌  خطأ HTTP من Hugging Face API: {exc}")
        print(f"    تفاصيل: {response.text[:300]}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 5. تحليل رد النموذج واستخراج JSON
# ---------------------------------------------------------------------------

def parse_model_response(raw_text: str) -> dict:
    """
    يحاول استخراج كائن JSON صالح من النص الخام الصادر عن النموذج.
    يتعامل مع حالات تغليف النص بـ Markdown code fence.
    """
    # إزالة أي تغليف Markdown من نوع ```json ... ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).replace("```", "").strip()

    # المحاولة الأولى: تحليل مباشر
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # المحاولة الثانية: البحث عن أول كتلة JSON في النص
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"تعذّر استخراج JSON صالح من رد النموذج:\n{raw_text}")


# ---------------------------------------------------------------------------
# 6. طباعة القصة بشكل منظم وجميل
# ---------------------------------------------------------------------------

def print_story(story_data: dict) -> None:
    """يطبع القصة النهائية بتنسيق بصري جميل في الطرفية."""
    separator = "═" * 60

    print(f"\n{separator}")
    print("✨  القصة الناتجة من نموذج Mistral-7B  ✨")
    print(separator)

    print(f"\n📰  العنوان:\n    {story_data.get('title', 'N/A')}")
    print(f"\n📖  القصة:\n    {story_data.get('story', 'N/A')}")
    print(f"\n🔬  حقيقة علمية:\n    {story_data.get('science_fact', 'N/A')}")
    print(f"\n💬  دعوة للتفاعل:\n    {story_data.get('call_to_action', 'N/A')}")

    print(f"\n{separator}\n")

    print("📦  بيانات JSON الكاملة:")
    print(json.dumps(story_data, ensure_ascii=False, indent=2))
    print(f"\n{separator}\n")


# ---------------------------------------------------------------------------
# نقطة الدخول الرئيسية
# ---------------------------------------------------------------------------

def main() -> None:
    # الخطوة 1: جلب بيانات APOD
    apod_data = fetch_apod_data()

    # الخطوة 2: تحويل البيانات إلى الصيغة المطلوبة
    event_json = apod_to_event_json(apod_data)
    print(f"\n📡  بيانات الحدث المُعدّة للإرسال:\n{json.dumps(event_json, ensure_ascii=False, indent=2)}")

    # الخطوة 3: إرسال البيانات إلى نموذج Mistral عبر Hugging Face
    try:
        raw_response = call_huggingface_model(event_json)
        print(f"\n📥  الرد الخام من النموذج:\n{raw_response}")
    except Exception as exc:
        print(f"❌  خطأ غير متوقع أثناء الاتصال بـ Hugging Face: {exc}")
        sys.exit(1)

    # الخطوة 4: تحليل رد النموذج
    try:
        story_data = parse_model_response(raw_response)
    except ValueError as exc:
        print(f"❌  {exc}")
        sys.exit(1)

    # الخطوة 5: طباعة القصة النهائية
    print_story(story_data)


if __name__ == "__main__":
    main()
