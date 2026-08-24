import SpaceChat from '@/components/chat/SpaceChat';

export const metadata = {
  title: 'المحادثة — Space Interpreter',
  description: 'تحدّث مع مساعد فلكي عربي — اسأل عن النجوم والكواكب والمجرات والكون.',
};

export default function ChatPage() {
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
        <header lang="ar" dir="rtl" style={{ marginBottom: '28px' }}>
          <div className="section-chip" style={{ marginBottom: '16px' }}>
            AI Assistant · مساعد فلكي
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
            مساعدك لاستكشاف الكون
          </h1>
          <p style={{
            fontSize: 'clamp(13px, 2vw, 15px)',
            color: 'var(--text-muted)',
            margin: 0,
            lineHeight: 1.8,
          }}>
            اسأل عن النجوم والمجرات والكواكب والظواهر الكونية.
          </p>
        </header>

        {/* Chat */}
        <SpaceChat />

        {/* Scientific note */}
        <div
          lang="ar"
          dir="rtl"
          style={{
            padding: '16px 20px',
            marginTop: '16px',
            background: 'rgba(122,44,255,0.03)',
            border: '1px solid rgba(122,44,255,0.1)',
            borderRadius: '10px',
          }}
        >
          <p style={{ fontSize: '12px', color: 'var(--text-faint)', margin: 0, lineHeight: 1.8 }}>
            <span style={{ color: 'rgba(122,44,255,0.7)', marginLeft: '6px' }}>✦</span>
            يلتزم المساعد بالدقة العلمية ويميّز بين الحقائق المثبتة والتفسيرات الاحتمالية. عند الشك، يقول ذلك صراحةً.
          </p>
        </div>
      </div>
    </div>
  );
}
