import ImageAnalyzer from '@/components/image-analyzer/ImageAnalyzer';

export const metadata = {
  title: 'المترجم الفضائي — Space Interpreter',
  description: 'ارفع صورة فضائية واحصل على تفسير علمي عربي مفصّل بالذكاء الاصطناعي.',
};

export default function InterpreterPage() {
  return (
    <div style={{ background: 'var(--deep-space)', minHeight: '100vh' }}>
      <div
        style={{
          maxWidth: '820px',
          margin: '0 auto',
          padding: 'clamp(32px, 5vw, 60px) clamp(16px, 4vw, 40px) clamp(40px, 6vw, 80px)',
        }}
      >
        {/* Page header */}
        <header lang="ar" dir="rtl" style={{ marginBottom: '36px' }}>
          <div className="section-chip" style={{ marginBottom: '16px' }}>
            Vision AI · تحليل بصري
          </div>
          <h1
            style={{
              fontSize: 'clamp(22px, 4vw, 34px)',
              fontWeight: 700,
              color: 'var(--stellar-white)',
              margin: '0 0 12px',
              lineHeight: 1.3,
            }}
          >
            المترجم الفضائي
          </h1>
          <p style={{
            fontSize: 'clamp(13px, 2vw, 15px)',
            color: 'var(--text-muted)',
            margin: 0,
            lineHeight: 1.8,
            maxWidth: '560px',
          }}>
            ارفع صورة من الكون ودع الذكاء الاصطناعي يساعدك على فهم ما تراه.
          </p>
        </header>

        {/* Main analyzer */}
        <div className="space-card" style={{ padding: 'clamp(20px, 4vw, 32px)', marginBottom: '20px' }}>
          <ImageAnalyzer />
        </div>

        {/* Tips card */}
        <div
          lang="ar"
          dir="rtl"
          style={{
            padding: '18px 22px',
            background: 'rgba(0,217,255,0.03)',
            border: '1px solid rgba(0,217,255,0.1)',
            borderRadius: '12px',
          }}
        >
          <h3 style={{
            fontSize: '11px',
            fontWeight: 700,
            color: 'var(--pulsar-blue)',
            margin: '0 0 10px',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}>
            نصائح للحصول على أفضل تحليل
          </h3>
          <ul style={{
            margin: 0,
            padding: '0 16px 0 0',
            listStyle: 'disc',
            color: 'var(--text-muted)',
            fontSize: '13px',
            lineHeight: 1.95,
          }}>
            <li>استخدم صوراً واضحة وعالية الدقة من ناسا أو مراصد فلكية</li>
            <li>اطرح سؤالاً محدداً للحصول على إجابة مفصّلة</li>
            <li>الصيغ المدعومة: JPEG · PNG · WEBP (حد أقصى 5 ميغابايت)</li>
            <li>النظام يميّز بين ما يُشاهَد في الصورة وما يمكن استنتاجه علمياً</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
