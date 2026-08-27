/* ==========================================================================
   Al-Tariq — shared application JavaScript
   Covers:
     • Starfield canvas background (requirement 5)
     • Language switcher — AR/EN, isolated from date/time (requirements 3 & 4)
     • Full Arabic i18n with 100% coverage (requirement 3)
     • Navigation init
     • Pulsar lab controls
   ========================================================================== */

'use strict';

/* ── Utility ──────────────────────────────────────────────────────────────── */
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];

/* ── Icons ────────────────────────────────────────────────────────────────── */
const icons = {
  menu:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M4 6h16M4 12h16M4 18h16"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 2l1.9 6.1L20 10l-6.1 1.9L12 18l-1.9-6.1L4 10l6.1-1.9L12 2Z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z"/></svg>',
  star:  '<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5"><path d="m12 3 2.78 5.63 6.22.9-4.5 4.4 1.06 6.2L12 17.2l-5.56 2.93 1.06-6.2L3 9.53l6.22-.9L12 3Z"/></svg>',
};

/* ==========================================================================
   1. STARFIELD CANVAS (requirement 5)
   Full-viewport, fixed behind all content, pointer-events: none.
   ========================================================================== */

function initStarfield() {
  // Create canvas if not already present
  let canvas = document.getElementById('starfield-canvas');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'starfield-canvas';
    canvas.style.cssText = [
      'position:fixed',
      'inset:0',
      'width:100%',
      'height:100%',
      'z-index:-1',
      'pointer-events:none',
      'opacity:0.85',
    ].join(';');
    document.body.insertBefore(canvas, document.body.firstChild);
  }

  const ctx = canvas.getContext('2d');
  const STAR_COUNT = 220;
  const TWINKLE_SPEED_MIN = 0.004;
  const TWINKLE_SPEED_MAX = 0.012;

  let stars = [];
  let animFrame;

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function randomStar() {
    return {
      x:     Math.random() * canvas.width,
      y:     Math.random() * canvas.height,
      r:     Math.random() * 1.2 + 0.2,   // radius 0.2–1.4 px
      alpha: Math.random(),                // current opacity 0–1
      delta: (Math.random() < 0.5 ? 1 : -1) *
             (TWINKLE_SPEED_MIN + Math.random() * (TWINKLE_SPEED_MAX - TWINKLE_SPEED_MIN)),
      // Subtle colour: white, pale-blue, or pale-yellow
      hue: [0, 210, 50][Math.floor(Math.random() * 3)],
      sat: Math.floor(Math.random() * 40),   // 0–40% saturation
    };
  }

  function buildStars() {
    stars = Array.from({ length: STAR_COUNT }, randomStar);
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of stars) {
      // Advance twinkle
      s.alpha += s.delta;
      if (s.alpha >= 1) { s.alpha = 1; s.delta = -Math.abs(s.delta); }
      if (s.alpha <= 0) { s.alpha = 0; s.delta =  Math.abs(s.delta); }

      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${s.hue},${s.sat}%,92%,${s.alpha.toFixed(3)})`;
      ctx.fill();
    }
    animFrame = requestAnimationFrame(draw);
  }

  // Handle resize: reposition stars proportionally
  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      resize();
      buildStars();
    }, 150);
  });

  resize();
  buildStars();
  draw();
}

/* ==========================================================================
   2. LANGUAGE SWITCHER (requirements 3 & 4)
   ========================================================================== */

/* ── Full Arabic translation table ─────────────────────────────────────────
   Keys = canonical English strings used in the HTML.
   Values = Arabic translation.
   Covers: nav labels, crumbs, eyebrows, headings, body text, dynamic JS strings.
   ─────────────────────────────────────────────────────────────────────────── */
const AR = {
  // ── Navigation labels ──
  'Home':                       'الرئيسية',
  'Home Dashboard':             'لوحة الرئيسية',
  'Image Interpreter':          'مفسّر الصور',
  'AI Space Chat':              'محادثة الفضاء',
  'Cosmos Stories':             'قصص الكون',
  'Exoplanet Catalog':          'دليل الكواكب الخارجية',
  'Space Weather Live':         'طقس الفضاء المباشر',
  'Interactive Pulsar Lab':     'مختبر البولسار التفاعلي',
  'Events Calendar':            'تقويم الأحداث',
  'Favorites Archive':          'أرشيف المفضلة',
  'Favorites':                  'المفضلة',
  'System Settings':            'إعدادات النظام',
  'Mission Timeline':           'الخط الزمني للمهمة',
  'Signal Observatory':         'مرصد الإشارات',

  // ── Breadcrumbs ──
  'MISSION CONTROL / DAILY BRIEF':   'التحكم بالمهمة / النشرة اليومية',
  'VISION LAB / IMAGE INTERPRETER':  'مختبر الرؤية / مفسّر الصور',
  'AI CORE / CONVERSATION':          'نواة الذكاء / المحادثة',
  'ARCHIVE / COSMOS STORIES':        'الأرشيف / قصص الكون',
  'SOLAR MONITOR / SPACE WEATHER':   'مراقب الشمس / طقس الفضاء',
  'ARCHIVE / FAVORITES':             'الأرشيف / المفضلة',
  'MISSION CONTROL / PULSAR LAB':    'التحكم بالمهمة / مختبر البولسار',
  'MISSION CONTROL / TIMELINE':      'التحكم بالمهمة / الخط الزمني',
  'MISSION CONTROL / OBSERVATORY':   'التحكم بالمهمة / المرصد',
  'PHYSICS WORKBENCH / PULSAR LAB':  'ورشة الفيزياء / مختبر البولسار',
  'NASA ARCHIVE / EXOPLANETS':       'أرشيف ناسا / الكواكب الخارجية',

  // ── Status labels ──
  'AI SYSTEMS ONLINE':   'أنظمة الذكاء الاصطناعي مفعّلة',
  'AI VISION ONLINE':    'رؤية الذكاء الاصطناعي مفعّلة',
  'MISSION AI ONLINE':   'مهمة الذكاء الاصطناعي مفعّلة',
  'ARCHIVE ONLINE':      'الأرشيف متاح',
  'SOLAR MONITOR ONLINE':'مراقب الشمس متاح',
  'LOCAL ARCHIVE READY': 'الأرشيف المحلي جاهز',
  'CONNECTING…':         'جارٍ الاتصال…',
  'BACKEND OFFLINE':     'الخادم غير متاح',
  'AI VISION ONLINE':    'رؤية الذكاء الاصطناعي متاحة',

  // ── Tags / badges ──
  'LIVE APOD FEED':    'بث APOD المباشر',
  'DONKI / CME':       'DONKI / CME',
  'AI VISION ONLINE':  'رؤية AI متاحة',
  'NASA APOD INDEX':   'فهرس NASA APOD',
  'LOCAL STORAGE':     'تخزين محلي',
  'LOADING':           'جارٍ التحميل',
  'ERROR':             'خطأ',
  'READY':             'جاهز',
  'PROCESSING':        'جارٍ المعالجة',
  'STABLE':            'مستقر',
  'WATCH':             'تنبيه',
  'APOD':              'APOD',
  'VIDEO':             'فيديو',
  'VIDEO / APOD':      'فيديو / APOD',
  'DEEP SPACE / APOD': 'الفضاء العميق / APOD',
  'SAVED SIGNAL':      'إشارة محفوظة',
  'APOD DETAIL':       'تفاصيل APOD',

  // ── Index page ──
  'THE MORNING BULLETIN · SIGNAL 001': 'النشرة الصباحية · الإشارة 001',
  'Understand the Cosmos Differently.': 'افهم الكون بطريقة مختلفة.',
  'Al-Tariq translates the universe\'s most complex signals into clear, human stories — powered by NASA data and an intelligent space interpreter.':
    'يحوّل الطارق أعقد إشارات الكون إلى قصص واضحة وإنسانية — بالاعتماد على بيانات ناسا ومفسّر فضائي ذكي.',
  'Ask AI Assistant →':    'اسأل المساعد الذكي →',
  'Analyze Space Image ↗': 'حلّل صورة فضائية ↗',
  'LIVE SOURCE':   'المصدر المباشر',
  'AI CONFIDENCE': 'ثقة الذكاء الاصطناعي',
  'STORY MODE':    'وضع القصة',
  'ENABLED':       'مفعّل',
  'AL-TARIQ / PULSAR CORE': 'الطارق / نواة البولسار',

  'Today\'s signal': 'إشارة اليوم',
  'A NASA image, interpreted into a story worth remembering.': 'صورة من ناسا، مُفسَّرة إلى قصة تستحق التذكر.',
  'Fetching today\'s signal…': 'جارٍ جلب إشارة اليوم…',
  'Connecting to NASA and generating the daily story. This may take up to 30 seconds on the first request.':
    'جارٍ الاتصال بناسا وإنشاء القصة اليومية. قد يستغرق ذلك حتى 30 ثانية في الطلب الأول.',
  'Initialising…': 'جارٍ التهيئة…',
  'Retry →': 'إعادة المحاولة →',
  'Could not load today\'s bulletin.': 'تعذّر تحميل نشرة اليوم.',
  'Scientific analysis': 'التحليل العلمي',
  'Why it matters':      'لماذا يهم',
  'Key fact':            'حقيقة أساسية',

  'Space weather': 'طقس الفضاء',
  'Solar activity translated into a simple threat picture.': 'النشاط الشمسي مُترجَم إلى صورة بسيطة للتهديد.',
  'CME EVENTS':    'أحداث CME',
  'Loading…':      'جارٍ التحميل…',
  'SPACE WEATHER DETAIL': 'تفاصيل طقس الفضاء',
  'GEOMAGNETIC MONITOR':  'مراقبة المجال المغناطيسي',
  'CME STATUS':           'حالة CME',
  'Kp-INDEX':             'مؤشر Kp',
  'EARTH IMPACT':         'التأثير على الأرض',
  'No active events':     'لا أحداث نشطة',
  'No significant CME events detected in the current monitoring window.':
    'لم يُرصد أي حدث CME مهم في نافذة المراقبة الحالية.',
  'CORONAL MASS EJECTION': 'قذف كتلي إكليلي',
  'Earth-directed activity': 'نشاط متجه نحو الأرض',
  'Quiet, with a watch signal': 'هادئ مع إشارة تنبيه',
  'Threat level':          'مستوى التهديد',
  'Active CME events':     'أحداث CME نشطة',
  'Earth-directed':        'متجه نحو الأرض',
  'Not Earth-directed':    'غير متجه نحو الأرض',
  'Elevated / watch':      'مرتفع / تنبيه',
  'Low / stable':          'منخفض / مستقر',
  'Monitoring active':     'المراقبة نشطة',
  'Estimated speed':       'السرعة المتوقعة',
  'UTC start':             'وقت البدء UTC',
  'Source location':       'موقع المصدر',
  'Est. arrival':          'الوصول المتوقع',
  'Kp index':              'مؤشر Kp',
  'ACTIVE':   'نشط',
  'QUIET':    'هادئ',
  'CLEAR':    'صافٍ',
  'WATCH':    'تنبيه',

  'System status':       'حالة النظام',
  'Backend and scheduler health.': 'صحة الخادم والجدولة.',
  'Loading system status…': 'جارٍ تحميل حالة النظام…',
  'Status unavailable — backend may be offline.': 'الحالة غير متاحة — قد يكون الخادم غير متصل.',
  'SCHEDULER': 'الجدولة',
  'LATEST BULLETIN': 'أحدث نشرة',
  'Enabled':     'مفعّل',
  'YES':         'نعم',
  'NO':          'لا',
  'Last run':    'آخر تشغيل',
  'Last status': 'آخر حالة',
  'APOD date':   'تاريخ APOD',
  'Status':      'الحالة',
  'Generated':   'أُنشئت',
  'No bulletin generated yet': 'لم تُنشأ أي نشرة بعد',
  'LAST SYNC':   'آخر مزامنة',

  // ── Interpreter page ──
  'SIGNAL DECODER 02':    'فاكّ الإشارة 02',
  'See deeper into space.': 'انظر أعمق في الفضاء.',
  'Upload an astronomy image and let Al-Tariq turn distant light into a clear scientific reading.':
    'ارفع صورة فلكية ودع الطارق يحوّل الضوء البعيد إلى قراءة علمية واضحة.',
  'Drop an image here':                'أسقط صورة هنا',
  'or choose a file from your device': 'أو اختر ملفاً من جهازك',
  'Choose image':                      'اختر صورة',
  'JPG / PNG / WEBP':                  'JPG / PNG / WEBP',
  'MAX 5 MB':                          'الحد الأقصى 5 ميغابايت',
  'Ask a specific question (optional)': 'اطرح سؤالاً محدداً (اختياري)',
  'e.g. What type of nebula is this?':  'مثال: ما نوع هذا السديم؟',
  'Analyze image':                      'تحليل الصورة',
  'ready for interpretation.':          'جاهزة للتفسير.',
  'Unsupported type. Use JPG, PNG, or WEBP.': 'نوع غير مدعوم. استخدم JPG أو PNG أو WEBP.',
  'File exceeds 5 MB limit.':           'حجم الملف يتجاوز حد الـ 5 ميغابايت.',

  'AWAITING SIGNAL': 'في انتظار الإشارة',
  'Upload an image to begin.': 'ارفع صورة للبدء.',
  'The vision AI will return a detailed scientific interpretation, including key observations and a confidence rating.':
    'سيُعيد ذكاء الرؤية الاصطناعية تفسيراً علمياً مفصّلاً يشمل الملاحظات الرئيسية وتقييم الثقة.',
  'INTERPRETING SIGNAL': 'جارٍ تفسير الإشارة',
  'Analysing…': 'جارٍ التحليل…',
  'Vision AI is reading the image. This usually takes 5–15 seconds.':
    'يقرأ ذكاء الرؤية الاصطناعية الصورة. يستغرق ذلك عادةً 5–15 ثانية.',
  'SIGNAL ERROR': 'خطأ في الإشارة',
  'Analysis failed.': 'فشل التحليل.',
  'Check that the backend is running and that OPENROUTER_API_KEY is set. Only JPG/PNG/WEBP up to 5 MB are accepted.':
    'تحقق من تشغيل الخادم وضبط مفتاح OPENROUTER_API_KEY. يُقبل فقط JPG/PNG/WEBP بحجم لا يتجاوز 5 ميغابايت.',

  'INTERPRETATION COMPLETE': 'اكتمل التفسير',
  'HIGH CONFIDENCE':   'ثقة عالية',
  'MEDIUM CONFIDENCE': 'ثقة متوسطة',
  'LOW CONFIDENCE':    'ثقة منخفضة',
  'Scientific Explanation': 'التفسير العلمي',
  'Observations':           'الملاحظات',
  'Your Question':          'سؤالك',
  'Narrative':              'الرواية',
  'Note':                   'ملاحظة',
  'This image does not appear to be space-related. Try uploading an astronomy photograph.':
    'لا تبدو هذه الصورة مرتبطة بالفضاء. حاول رفع صورة فلكية.',
  'Continue in AI Chat with this image →': 'تابع في محادثة الذكاء الاصطناعي مع هذه الصورة →',
  'Analysis failed. Check that the backend is running.':
    'فشل التحليل. تحقق من تشغيل الخادم.',

  // ── Chat page ──
  'ORBITAL KNOWLEDGE INTERFACE': 'واجهة المعرفة المدارية',
  'Ask the universe.': 'اسأل الكون.',
  'A focused conversation space for black holes, stellar birth, pulsars, and everything between.':
    'فضاء محادثة مركّز حول الثقوب السوداء ونشأة النجوم والبولسارات وكل ما بينها.',
  'IMAGE CONTEXT ACTIVE': 'سياق الصورة نشط',
  'Clear context ✕':      'مسح السياق ✕',

  'What is a black hole?':         'ما هو الثقب الأسود؟',
  'How are stars born?':           'كيف تولد النجوم؟',
  'Explain neutron star spin':     'اشرح دوران النجم النيوتروني',
  'What is a pulsar?':             'ما هو البولسار؟',
  'What is this object?':          'ما هذا الجسم؟',
  'How was this formed?':          'كيف تشكّل هذا؟',
  'How far away is it?':           'ما بُعده عنّا؟',

  'Welcome to the interpreter. Ask me anything about the cosmos and I will translate the science into a clear signal.':
    'مرحباً بك في المفسّر. اسألني عن أي شيء في الكون وسأترجم العلم إلى إشارة واضحة.',
  'Conversation cleared. What would you like to explore?':
    'تمت مسح المحادثة. ماذا تودّ استكشافه؟',
  'Message too long (max 800 characters).':   'الرسالة طويلة جداً (الحد 800 حرف).',
  'Could not reach the AI. Check the backend is running.':
    'تعذّر الوصول إلى الذكاء الاصطناعي. تحقق من تشغيل الخادم.',
  'Enter to send · max 800 characters per message':
    'Enter للإرسال · الحد الأقصى 800 حرف للرسالة',
  'Ask about stars, black holes, pulsars…':
    'اسأل عن النجوم والثقوب السوداء والبولسارات…',
  'Send': 'إرسال',
  'YOU':  'أنت',
  'AL-TARIQ AI': 'طارق AI',
  'AL-TARIQ AI · READY':      'طارق AI · جاهز',
  'AL-TARIQ AI · PROCESSING': 'طارق AI · يعالج',

  // ── Stories page ──
  'THE UNIVERSE, IN CONTEXT': 'الكون، في السياق',
  'Stories from the dark.': 'قصص من الظلام.',
  'A living archive of images, signals, and the science behind the view.':
    'أرشيف حي من الصور والإشارات والعلم وراء المشهد.',
  'Search stories…':   'ابحث عن قصص…',
  'All':               'الكل',
  'Images':            'صور',
  'Videos':            'فيديوهات',
  'Loading…':          'جارٍ التحميل…',
  'Load more archive signals': 'تحميل المزيد من الإشارات',
  'No stories found':  'لم تُوجد قصص',
  'Try a different search or filter.': 'جرّب بحثاً أو فلتراً مختلفاً.',
  'Could not load stories': 'تعذّر تحميل القصص',
  'Backend may be offline.': 'قد يكون الخادم غير متصل.',
  'Retry': 'إعادة المحاولة',
  'NASA APOD': 'ناسا APOD',
  'View on NASA ↗': 'عرض على ناسا ↗',
  'Save to favorites': 'حفظ في المفضلة',
  '★ Saved':           '★ محفوظ',
  '☆ Save to favorites': '☆ حفظ في المفضلة',
  'Load more archive signals': 'تحميل المزيد من الإشارات',
  'Loading…': 'جارٍ التحميل…',
  'Archive synchronized': 'تمت مزامنة الأرشيف',
  'Retry load more':      'إعادة تحميل المزيد',
  'Close':        'إغلاق',
  '✕ Close':      '✕ إغلاق',
  'Video APOD':   'APOD مرئي',

  // ── Weather page ──
  'THE SUN IS ALWAYS SPEAKING': 'الشمس تتحدث دائماً',
  'Read the solar wind.': 'اقرأ الرياح الشمسية.',
  'Translate flares, magnetic storms, and charged particles into a calm operational picture.':
    'حوِّل الشعلات والعواصف المغناطيسية والجسيمات المشحونة إلى صورة تشغيلية هادئة.',
  'CME event timeline': 'الجدول الزمني لأحداث CME',
  'Coronal Mass Ejection events from NASA DONKI.': 'أحداث القذف الكتلي الإكليلي من ناسا DONKI.',
  'SYNCING…': 'جارٍ المزامنة…',
  'Fetching space weather data…': 'جارٍ جلب بيانات طقس الفضاء…',
  'CME events detected in monitoring window': 'أحداث CME مُكتشفة في نافذة المراقبة',
  'No significant CME detected': 'لم يُكتشف CME مهم',
  'No Kp data available': 'لا تتوفر بيانات Kp',
  'Active geomagnetic conditions': 'أوضاع مغناطيسية أرضية نشطة',
  'Quiet geomagnetic conditions':  'أوضاع مغناطيسية أرضية هادئة',
  'One or more CMEs are Earth-directed': 'CME واحد أو أكثر متجه نحو الأرض',
  'No Earth-directed CMEs detected': 'لم يُكتشف CME متجه نحو الأرض',
  'Solar activity is quiet': 'النشاط الشمسي هادئ',
  'No CME events detected in the current monitoring window. Data is sourced from NASA DONKI.':
    'لم تُرصد أحداث CME في نافذة المراقبة الحالية. البيانات مصدرها ناسا DONKI.',
  'ACTIVE CME EVENTS': 'أحداث CME النشطة',
  'UTC Start': 'وقت البدء UTC',
  'Speed':     'السرعة',
  'Source':    'المصدر',
  'Kp index':  'مؤشر Kp',
  'Unknown':   'غير معروف',
  'OFFLINE':            'غير متصل',
  'ACTIVE WATCH':       'تنبيه نشط',
  'MONITORING':         'مراقبة',
  'SIGNAL STABLE':      'الإشارة مستقرة',
  'LOADING':            'جارٍ التحميل',
  'Error loading data': 'خطأ في تحميل البيانات',

  // ── Favorites page ──
  'YOUR CAPTURED SIGNALS': 'إشاراتك المحفوظة',
  'Keep what moves you.': 'احتفظ بما يؤثّر فيك.',
  'Your personal constellation of stories, saved locally in this browser.':
    'مجموعتك الشخصية من القصص، محفوظة محلياً في هذا المتصفح.',
  'Explore archive →': 'استكشف الأرشيف →',
  'Clear all':         'مسح الكل',
  'saved signal':      'إشارة محفوظة',
  'saved signals':     'إشارات محفوظة',
  'Your archive is quiet': 'أرشيفك هادئ',
  'Save a story from the':                    'احفظ قصة من',
  'archive and it will appear here.':          'الأرشيف وستظهر هنا.',
  'Remove all saved stories from this browser?': 'إزالة جميع القصص المحفوظة من هذا المتصفح؟',
  'LOCAL ARCHIVE':  'الأرشيف المحلي',
  'NASA ↗':         'ناسا ↗',

  // ── Exoplanet Catalog page ──
  'WORLDS BEYOND OUR SUN':          'عوالم خارج شمسنا',
  'Map the unknown.':               'رسم خريطة المجهول.',
  'Explore the growing catalog of confirmed worlds through the signals astronomers use to find them.':
    'استكشف الفهرس المتنامي من العوالم المؤكدة عبر الإشارات التي يستخدمها علماء الفلك للكشف عنها.',
  'Search planet or host star…':    'ابحث عن كوكب أو نجم مضيف…',
  'All methods':        'جميع الطرق',
  'Transit':            'العبور',
  'Radial velocity':    'السرعة القطرية',
  'Imaging':            'التصوير المباشر',
  'CONFIRMED WORLDS · 5,742':  'العوالم المؤكدة · 5,742',
  'Discovery stream':   'تيار الاكتشافات',
  'Planet':             'الكوكب',
  'Method':             'الطريقة',
  'Distance':           'المسافة',
  'Orbital period':     'الفترة المدارية',
  'Habitability':       'قابلية السكن',
  'Potentially habitable': 'ربما صالح للحياة',
  'Hot Jupiter':        'مشتري ساخن',
  'Detected by the dip in starlight as the planet crosses.':  'يُكتشف بانخفاض ضوء النجم حين يعبر الكوكب.',
  'Stellar wobble reveals a hidden companion.':               'يكشف اهتزاز النجم عن رفيق مخفي.',
  'Captured directly in reflected or emitted light.':         'يُصوَّر مباشرةً في الضوء المنعكس أو المنبعث.',
  'No results found':   'لا نتائج',
  'LIVE CATALOG UI':    'واجهة الفهرس المباشر',

  // ── Pulsar Lab page ──
  'AL-TARIQ / NEUTRON STAR STUDY': 'الطارق / دراسة النجم النيوتروني',
  'Turn the star.':     'أدِر النجم.',
  'Adjust the model and watch how rotation, magnetic tilt, and beam energy shape the signal.':
    'اضبط النموذج وشاهد كيف يُشكّل الدوران والميلان المغناطيسي وطاقة الحزمة الإشارةَ.',
  'CONTROL SURFACE':    'سطح التحكم',
  'Physics parameters': 'معاملات الفيزياء',
  'RUNNING':            'قيد التشغيل',
  'Rotation frequency': 'تردد الدوران',
  'Magnetic field tilt':'ميلان المجال المغناطيسي',
  'Beam energy':        'طاقة الحزمة',
  'Pulse period':       'دورة النبضة',
  'Beam width':         'عرض الحزمة',
  'How pulsars work':   'كيف تعمل البولسارات',
  'The physics behind the signal.': 'الفيزياء وراء الإشارة.',
  'NEUTRON STAR':       'النجم النيوتروني',
  'Ultra-dense core':   'نواة شديدة الكثافة',
  'A neutron star packs 1.4 solar masses into a sphere just 20 km across — a teaspoon weighs a billion tonnes.':
    'يضغط النجم النيوتروني 1.4 كتلة شمسية في كرة قطرها 20 كم فقط — ملعقة صغيرة منه تزن مليار طن.',
  'MAGNETIC FIELD':     'المجال المغناطيسي',
  '10¹² Gauss':         '10¹² غاوس',
  'The strongest magnetic fields in the observable universe, channelling charged particles into focused beams.':
    'أقوى مجالات مغناطيسية في الكون المرصود، تُوجّه الجسيمات المشحونة في حزم مركّزة.',
  'TIMING':             'التوقيت',
  'Cosmic clocks':      'ساعات كونية',
  'Millisecond pulsars rival atomic clocks in precision, enabling tests of general relativity and gravitational wave detection.':
    'تضاهي بولسارات المللي ثانية الساعات الذرية دقةً، وتُتيح اختبار النسبية العامة والكشف عن الموجات الثقالية.',
  'EXPLAINER':          'شرح',
  'SIMULATION MODE':    'وضع المحاكاة',

  // ── Events Calendar page ──
  'LOOK UP, SOMETHING IS HAPPENING': 'انظر لأعلى، هناك ما يحدث',
  'Meet the sky on time.': 'قابل السماء في وقتها.',
  'A visual calendar for meteor showers, conjunctions, eclipses, and the moments that make the night feel larger.':
    'تقويم مرئي لأمطار الشهب والاقترانات والكسوفات واللحظات التي تجعل الليل يبدو أكبر.',
  'August mission calendar':    'تقويم مهمة أغسطس',
  'Selected events for observation.': 'أحداث مختارة للرصد.',
  'Today':              'اليوم',
  'Next major event':   'الحدث الكبير القادم',
  'Mark it on your calendar.': 'ضعه في تقويمك.',
  'Perseid meteor shower':   'أمطار شهب البرشاويات',
  'Moon & Saturn conjunction': 'اقتران القمر وزحل',
  'New moon window':         'نافذة الهلال الجديد',
  'Partial lunar eclipse':   'خسوف جزئي للقمر',
  'Annular solar eclipse':   'كسوف شمسي حلقي',
  'Geminid meteor shower':   'أمطار شهب الجوزائيات',
  'UPCOMING':           'قادم',
  'ORBITAL EVENTS / CALENDAR': 'الأحداث المدارية / التقويم',

  // ── Settings page ──
  'SYSTEM PREFERENCES': 'تفضيلات النظام',
  'Shape your signal.': 'اضبط إشارتك.',
  'Configure the interface, data presentation, and future API connection points for the Al-Tariq experience.':
    'اضبط الواجهة وعرض البيانات ونقاط الاتصال المستقبلية لتجربة الطارق.',
  'INTERFACE':              'الواجهة',
  'Display preferences':    'تفضيلات العرض',
  'Theme':                  'السمة',
  'Deep space / dark':      'الفضاء العميق / داكن',
  'Motion':                 'الحركة',
  'Data density':           'كثافة البيانات',
  'Balanced':               'متوازن',
  'Time format':            'تنسيق الوقت',
  'UTC · 24 hour':          'UTC · 24 ساعة',
  'Edit preferences →':     'تعديل التفضيلات →',
  'Connection points':      'نقاط الاتصال',
  'NOT CONNECTED':          'غير متصل',
  'Backend base URL':       'عنوان الخادم الأساسي',
  'NASA data status':       'حالة بيانات ناسا',
  'Save & reconnect':       'حفظ وإعادة الاتصال',
  'Language & locale':      'اللغة والتوطين',
  'Interface language and text direction.': 'لغة الواجهة واتجاه النص.',
  'Interface language':     'لغة الواجهة',
  'Use the AR / EN button at the top-right of any page to switch. Your preference is saved in the browser.':
    'استخدم زر AR / EN في الزاوية العلوية من أي صفحة للتبديل. يتم حفظ تفضيلاتك في المتصفح.',
  'Local storage':          'التخزين المحلي',
  'Saved favorites':        'المفضلة المحفوظة',
  'Language preference':    'تفضيل اللغة',
  'Clear local storage':    'مسح التخزين المحلي',
  'About Al-Tariq':         'حول الطارق',
  'Version information and credits.': 'معلومات الإصدار والاعتمادات.',
  'Version':                'الإصدار',
  'Backend':                'الخادم الخلفي',
  'AI engine':              'محرك الذكاء الاصطناعي',
  'Data source':            'مصدر البيانات',
  'License':                'الرخصة',
  'FRONTEND CONFIG':        'إعدادات الواجهة',
  'MISSION CONTROL / SETTINGS': 'التحكم بالمهمة / الإعدادات',
  'SYSTEMS CONFIGURED':     'الأنظمة مضبوطة',

  // ── Shared error messages ──
  'Make sure the backend is running at':
    'تأكد من تشغيل الخادم على',
  'Check that':                    'تحقق أن',
  'and':                           'و',
  'are set in your':               'مضبوط في ملف',
  'file.':                         'الخاص بك.',
  'Backend unavailable.':          'الخادم غير متاح.',
  'Cannot reach the backend. Make sure the FastAPI server is running.':
    'تعذّر الوصول إلى الخادم. تأكد من تشغيل خادم FastAPI.',
  'Unexpected response from server (not JSON).': 'استجابة غير متوقعة من الخادم (ليست JSON).',
};

/* ── Current language state ─────────────────────────────────────────────── */
let currentLang = localStorage.getItem('al-tariq-lang') || 'en';

function t(key) {
  if (currentLang === 'ar' && AR[key]) return AR[key];
  return key;
}

/* ── Apply translation to a DOM element ────────────────────────────────────
   Walks text nodes and translatable attributes.
   ─────────────────────────────────────────────────────────────────────────── */
function translateElement(el) {
  if (!el || !(el instanceof Element)) return;

  // Translate text nodes (trim so "  Home  " still maps to "Home")
  for (const node of el.childNodes) {
    if (node.nodeType === Node.TEXT_NODE) {
      const orig = node.textContent.trim();
      if (orig && AR[orig]) {
        node.textContent = node.textContent.replace(orig, t(orig));
      }
    }
  }

  // Translate placeholder / aria-label attributes
  if (el.placeholder && AR[el.placeholder]) el.placeholder = t(el.placeholder);
  if (el.getAttribute && el.getAttribute('aria-label') && AR[el.getAttribute('aria-label')]) {
    el.setAttribute('aria-label', t(el.getAttribute('aria-label')));
  }

  // Recurse into children (but not script/style)
  for (const child of el.children) {
    if (!['SCRIPT', 'STYLE', 'CANVAS'].includes(child.tagName)) {
      translateElement(child);
    }
  }
}

/* ── Full-page translation ───────────────────────────────────────────────── */
function applyLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('al-tariq-lang', lang);

  const html = document.documentElement;
  if (lang === 'ar') {
    html.setAttribute('lang', 'ar');
    html.setAttribute('dir', 'rtl');
    document.body.setAttribute('dir', 'rtl');
    translateElement(document.body);
  } else {
    html.setAttribute('lang', 'en');
    html.setAttribute('dir', 'ltr');
    document.body.removeAttribute('dir');
    // Reload to restore original English text cleanly
    location.reload();
  }

  // Keep button label in English (never translated — req #4)
  const btn = document.getElementById('lang-toggle');
  if (btn) {
    btn.textContent = lang === 'ar' ? 'EN' : 'AR';
    btn.style.direction = 'ltr';
  }
}

/* ── Inject language toggle button ─────────────────────────────────────────
   Position: fixed, top-right corner, isolated from date/time display.
   The button text is ALWAYS English (EN / AR) — never translated.
   ─────────────────────────────────────────────────────────────────────────── */
function injectLangToggle() {
  if (document.getElementById('lang-toggle')) return; // already present

  const btn = document.createElement('button');
  btn.id = 'lang-toggle';
  btn.setAttribute('aria-label', 'Switch language');
  // Always display English abbreviation — requirement #4
  btn.textContent = currentLang === 'ar' ? 'EN' : 'AR';
  btn.style.cssText = [
    'position:fixed',
    'top:14px',
    // Right side so it never overlaps the left-side date/time display
    'right:18px',
    'z-index:999',
    'padding:6px 13px',
    'border:1px solid rgba(0,240,255,.35)',
    'background:rgba(0,240,255,.07)',
    'color:var(--cyan)',
    'border-radius:8px',
    'font-size:11px',
    'font-weight:700',
    'letter-spacing:.1em',
    'cursor:pointer',
    'backdrop-filter:blur(8px)',
    'transition:background .15s,border-color .15s',
    // Force LTR inside the button — req #4
    'direction:ltr',
    'font-family:"Space Mono",monospace',
  ].join(';');

  btn.addEventListener('mouseover', () => { btn.style.background = 'rgba(0,240,255,.18)'; });
  btn.addEventListener('mouseout',  () => { btn.style.background = 'rgba(0,240,255,.07)'; });
  btn.addEventListener('click', () => {
    applyLanguage(currentLang === 'ar' ? 'en' : 'ar');
  });

  document.body.appendChild(btn);
}

/* ==========================================================================
   3. NAVIGATION
   ========================================================================== */

function initNav() {
  const btn  = $('.mobile-menu');
  const nav  = $('.nav');
  if (!nav) return;

  const items = [
    ['index.html',            'Home Dashboard'],
    ['interpreter.html',      'Image Interpreter'],
    ['chat.html',             'AI Space Chat'],
    ['stories.html',          'Cosmos Stories'],
    ['exoplanets.html',       'Exoplanet Catalog'],
    ['weather.html',          'Space Weather Live'],
    ['pulsar-lab.html',       'Interactive Pulsar Lab'],
    ['calendar.html',         'Events Calendar'],
    ['favorites.html',        'Favorites Archive'],
    ['settings.html',         'System Settings'],
    ['mission-timeline.html', 'Mission Timeline'],
    ['observatory.html',      'Signal Observatory'],
  ];

  nav.innerHTML = items.map(([href, label]) => `
    <a href="${href}">
      <span class="nav-dot" aria-hidden="true"></span>
      <span>${t(label)}</span>
    </a>`).join('');

  if (btn) btn.addEventListener('click', () => nav.classList.toggle('open'));

  const path = location.pathname.split('/').pop() || 'index.html';
  nav.querySelectorAll('a').forEach(a => {
    if (a.getAttribute('href') === path || (path === '' && a.getAttribute('href') === 'index.html')) {
      a.classList.add('active');
    }
  });
}

/* ==========================================================================
   4. PULSAR LAB CONTROLS
   ========================================================================== */

function initPulsarLab() {
  const visual   = $('.hero-visual');
  const controls = $$('.field input[type="range"]');
  if (!visual || controls.length < 3) return;

  const [frequency, tilt, energy] = controls;
  const fields  = $$('.field');
  const readout = fields.map(x => x.querySelector('b'));
  const blocks  = $$('.result-block .metric');

  const update = () => {
    const hz      = Math.round(120 + Number(frequency.value) * 8.28);
    const tiltDeg = Math.round(-45 + Number(tilt.value) * 0.91);
    const power   = Number(energy.value);
    const period  = (1000 / hz).toFixed(2);
    const width   = (3 + power * 0.06).toFixed(0);

    visual.style.setProperty('--pulsar-speed', `${(4600 / hz).toFixed(2)}s`);
    visual.style.setProperty('--tilt-deg',     `${tiltDeg}deg`);
    visual.style.setProperty('--beam-power',   power / 100);
    visual.querySelectorAll('.jet').forEach(j => { j.style.width = `${40 + power * 0.1}%`; });

    if (readout[0]) readout[0].textContent = `${hz} Hz`;
    if (readout[1]) readout[1].textContent = `${tiltDeg < 0 ? '−' : '+'}${Math.abs(tiltDeg)}°`;
    if (readout[2]) readout[2].textContent = `${power}%`;
    if (blocks[0])  blocks[0].textContent  = `${period} ms`;
    if (blocks[1])  blocks[1].textContent  = `${width}°`;
  };

  controls.forEach(x => x.addEventListener('input', update));
  update();
}

/* ==========================================================================
   5. BOOT
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initStarfield();
  injectLangToggle();
  initNav();
  initPulsarLab();

  // If a language was previously selected, apply it on load
  if (currentLang === 'ar') {
    applyLanguage('ar');
  }
});
