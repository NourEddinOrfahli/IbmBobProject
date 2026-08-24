import type { CMEEventSummary } from '@/lib/types';

interface CMEEventCardProps {
  event: CMEEventSummary;
  index: number;
}

function formatSpeed(speed: number | null): string {
  if (speed === null) return 'غير محدد';
  return `${Math.round(speed).toLocaleString('ar-SA')} كم/ث`;
}

function formatDate(iso: string | null): string {
  if (!iso) return 'غير محدد';
  try {
    return new Date(iso).toLocaleString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export default function CMEEventCard({ event, index }: CMEEventCardProps) {
  const isEarth = event.is_earth_directed;

  return (
    <article
      lang="ar"
      dir="rtl"
      aria-label={`حدث انبعاث كتلي إكليلي رقم ${index + 1}`}
      style={{
        background: 'var(--bg-elevated)',
        border: `1px solid ${isEarth === true ? 'rgba(251,146,60,0.35)' : 'var(--border)'}`,
        borderRadius: '10px',
        padding: '16px',
        fontSize: '13px',
        color: 'var(--text-primary)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <span
          style={{
            fontWeight: 700,
            color: 'var(--accent-cyan)',
            fontSize: '13px',
          }}
        >
          انبعاث كتلي إكليلي {index + 1}
        </span>

        {isEarth !== null && (
          <span
            style={{
              padding: '2px 10px',
              borderRadius: '20px',
              fontSize: '11px',
              fontWeight: 600,
              background: isEarth
                ? 'rgba(251,146,60,0.12)'
                : 'rgba(74,222,128,0.1)',
              border: isEarth
                ? '1px solid rgba(251,146,60,0.3)'
                : '1px solid rgba(74,222,128,0.25)',
              color: isEarth ? '#fb923c' : '#4ade80',
            }}
          >
            {isEarth ? '⚠ متجه نحو الأرض' : '✓ غير متجه نحو الأرض'}
          </span>
        )}
      </div>

      {/* Fields grid */}
      <dl
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: '8px 16px',
          margin: 0,
        }}
      >
        <Field label="وقت البدء" value={formatDate(event.begin_time)} />
        <Field label="السرعة" value={formatSpeed(event.speed_kmps)} />
        {event.estimated_arrival && (
          <Field label="الوصول المتوقع" value={formatDate(event.estimated_arrival)} />
        )}
        {event.kp_index !== null && (
          <Field label="مؤشر Kp" value={String(event.kp_index)} />
        )}
        {event.source_location && (
          <Field label="موقع المصدر" value={event.source_location} />
        )}
      </dl>

      {/* Note */}
      {event.note && (
        <p
          style={{
            marginTop: '12px',
            fontSize: '12px',
            color: 'var(--text-muted)',
            borderTop: '1px solid var(--border)',
            paddingTop: '10px',
            lineHeight: 1.7,
          }}
        >
          {event.note}
        </p>
      )}
    </article>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>
        {label}
      </dt>
      <dd style={{ fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
        {value}
      </dd>
    </div>
  );
}
