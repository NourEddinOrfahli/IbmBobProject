/**
 * Skeleton loading state for the Space Dashboard.
 * Renders immediately — the API call may take 5–30 seconds.
 */
export default function BulletinSkeleton() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="جاري تحميل النشرة الفضائية…"
      lang="ar"
      dir="rtl"
      style={{ width: '100%' }}
    >
      {/* Screen-reader announcement */}
      <span className="sr-only">جاري تحميل النشرة الفضائية…</span>

      {/* Hero skeleton */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '16px',
          padding: '32px 28px',
          marginBottom: '24px',
        }}
      >
        {/* APOD badge */}
        <div className="skeleton" style={{ width: '100px', height: '24px', marginBottom: '20px' }} />

        {/* Image area */}
        <div className="skeleton" style={{ width: '100%', height: '280px', marginBottom: '24px', borderRadius: '10px' }} />

        {/* Title */}
        <div className="skeleton" style={{ width: '70%', height: '32px', marginBottom: '12px' }} />
        <div className="skeleton" style={{ width: '90%', height: '20px', marginBottom: '8px' }} />
        <div className="skeleton" style={{ width: '75%', height: '20px', marginBottom: '20px' }} />

        {/* Attribution */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div className="skeleton" style={{ width: '80px', height: '22px', borderRadius: '4px' }} />
          <div className="skeleton" style={{ width: '100px', height: '22px' }} />
        </div>
      </div>

      {/* Scientific story skeleton */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '16px',
          padding: '28px',
          marginBottom: '24px',
        }}
      >
        <div className="skeleton" style={{ width: '140px', height: '20px', marginBottom: '20px' }} />
        {[90, 100, 80, 95, 70].map((w, i) => (
          <div key={i} className="skeleton" style={{ width: `${w}%`, height: '16px', marginBottom: '10px' }} />
        ))}

        {/* Key facts */}
        <div style={{ marginTop: '24px' }}>
          <div className="skeleton" style={{ width: '80px', height: '18px', marginBottom: '14px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' }}>
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: '60px', borderRadius: '8px' }} />
            ))}
          </div>
        </div>
      </div>

      {/* Status skeleton */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: '16px',
          padding: '20px 28px',
        }}
      >
        <div className="skeleton" style={{ width: '120px', height: '18px', marginBottom: '16px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '12px' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: '48px', borderRadius: '8px' }} />
          ))}
        </div>
      </div>
    </div>
  );
}
