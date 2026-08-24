export default function BulletinEmpty() {
  return (
    <div
      lang="ar"
      dir="rtl"
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        padding: '56px 32px',
        textAlign: 'center',
        color: 'var(--text-primary)',
      }}
    >
      <div
        aria-hidden="true"
        style={{ fontSize: '52px', marginBottom: '20px' }}
      >
        🔭
      </div>

      <h2
        style={{
          fontSize: '20px',
          fontWeight: 700,
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}
      >
        النشرة الفضائية قيد الإعداد
      </h2>

      <p
        style={{
          fontSize: '14px',
          color: 'var(--text-muted)',
          maxWidth: '380px',
          margin: '0 auto',
          lineHeight: 1.9,
        }}
      >
        يقوم النظام حالياً باستقاء البيانات من ناسا وتوليد نشرة علمية عربية.
        يُرجى تحديث الصفحة بعد قليل.
      </p>
    </div>
  );
}
