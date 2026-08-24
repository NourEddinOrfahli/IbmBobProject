interface BulletinErrorProps {
  message: string | null;
  onRetry: () => void;
}

export default function BulletinError({ message, onRetry }: BulletinErrorProps) {
  // Use a safe, user-friendly message — never expose error codes
  const displayMessage =
    message && message.length < 200
      ? message
      : 'حدث خطأ أثناء تحميل النشرة الفضائية. يرجى المحاولة مجدداً.';

  return (
    <div
      role="alert"
      aria-live="polite"
      lang="ar"
      dir="rtl"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid rgba(248, 113, 113, 0.25)',
        borderRadius: '16px',
        padding: '48px 32px',
        textAlign: 'center',
        color: 'var(--text-primary)',
      }}
    >
      <div
        aria-hidden="true"
        style={{ fontSize: '48px', marginBottom: '16px' }}
      >
        🌑
      </div>

      <h2
        style={{
          fontSize: '18px',
          fontWeight: 700,
          color: '#f87171',
          marginBottom: '10px',
        }}
      >
        تعذّر تحميل النشرة
      </h2>

      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-muted)',
          marginBottom: '28px',
          maxWidth: '380px',
          margin: '0 auto 28px',
          lineHeight: 1.8,
        }}
      >
        {displayMessage}
      </p>

      <button
        onClick={onRetry}
        aria-label="إعادة محاولة تحميل النشرة الفضائية"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 24px',
          background: 'rgba(74, 158, 255, 0.1)',
          border: '1px solid rgba(74, 158, 255, 0.35)',
          borderRadius: '8px',
          color: 'var(--accent-blue)',
          fontSize: '14px',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'background 0.2s ease, border-color 0.2s ease',
          direction: 'rtl',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'rgba(74, 158, 255, 0.18)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'rgba(74, 158, 255, 0.1)';
        }}
      >
        <span aria-hidden="true">↺</span>
        حاول مجدداً
      </button>
    </div>
  );
}
