import type { SpaceWeatherSummary } from '@/lib/types';
import CMEEventCard from '@/components/ui/CMEEventCard';

interface SpaceWeatherSectionProps {
  data: SpaceWeatherSummary | null | undefined;
}

export default function SpaceWeatherSection({ data }: SpaceWeatherSectionProps) {
  // Null/undefined → don't render the section at all
  if (data === null || data === undefined) {
    return null;
  }

  const isEmpty = !data.available || data.events.length === 0;

  return (
    <section
      aria-labelledby="weather-heading"
      className="space-card"
      style={{ padding: '32px', marginBottom: '24px' }}
      lang="ar"
      dir="rtl"
    >
      <h2
        id="weather-heading"
        lang="ar"
        style={{
          fontSize: '16px',
          fontWeight: 700,
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <span aria-hidden="true">☀️</span>
        <span style={{ color: 'var(--accent-orange)' }}>الطقس الفضائي</span>
        {!isEmpty && (
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '12px',
              background: 'rgba(251, 146, 60, 0.12)',
              border: '1px solid rgba(251, 146, 60, 0.3)',
              color: 'var(--accent-orange)',
            }}
          >
            {data.event_count} {data.event_count === 1 ? 'حدث' : 'أحداث'}
          </span>
        )}
      </h2>

      {isEmpty ? (
        /* ── No active space weather events ────────────────── */
        <div
          style={{
            padding: '28px 20px',
            textAlign: 'center',
            color: 'var(--text-muted)',
            background: 'var(--bg-elevated)',
            borderRadius: '10px',
            border: '1px solid var(--border)',
          }}
        >
          <span aria-hidden="true" style={{ fontSize: '28px', display: 'block', marginBottom: '10px' }}>
            🌙
          </span>
          <p lang="ar" style={{ fontSize: '14px', margin: 0 }}>
            لا توجد أحداث فضائية نشطة حالياً
          </p>
        </div>
      ) : (
        /* ── CME event cards ───────────────────────────────── */
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '14px',
          }}
        >
          {data.events.map((event, i) => (
            <CMEEventCard key={i} event={event} index={i} />
          ))}
        </div>
      )}
    </section>
  );
}
