import type { StatusData } from '@/lib/types';

interface LiveStatusProps {
  data: StatusData | null;
  loading: boolean;
  error: string | null;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return 'لا يوجد';
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

function StatusDot({ status }: { status: string | null | undefined }) {
  const map: Record<string, { color: string; label: string }> = {
    success: { color: '#4ade80', label: 'ناجح' },
    failed: { color: '#f87171', label: 'فشل' },
    skipped: { color: '#fb923c', label: 'تجاوز' },
  };
  const cfg = status ? (map[status] ?? { color: '#7a99bf', label: status }) : null;
  if (!cfg) return <span style={{ color: 'var(--text-faint)' }}>—</span>;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '2px 8px',
        borderRadius: '12px',
        background: `${cfg.color}18`,
        border: `1px solid ${cfg.color}40`,
        color: cfg.color,
        fontSize: '12px',
        fontWeight: 600,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.color, display: 'inline-block' }} />
      {cfg.label}
    </span>
  );
}

function InfoItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: '8px',
        padding: '12px 14px',
      }}
    >
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
        {children}
      </div>
    </div>
  );
}

export default function LiveStatus({ data, loading, error }: LiveStatusProps) {
  if (loading) {
    return (
      <section
        aria-labelledby="status-heading"
        className="space-card"
        style={{ padding: '24px 28px' }}
        lang="ar"
        dir="rtl"
      >
        <h2
          id="status-heading"
          lang="ar"
          style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '14px' }}
        >
          حالة النشرة
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '10px' }}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton" style={{ height: '56px', borderRadius: '8px' }} />
          ))}
        </div>
      </section>
    );
  }

  // Status endpoint failed — show subtle degraded state, not a blocking error
  if (error || !data) {
    return (
      <section
        className="space-card"
        style={{ padding: '18px 28px' }}
        lang="ar"
        dir="rtl"
      >
        <p style={{ fontSize: '12px', color: 'var(--text-faint)', margin: 0 }}>
          حالة النظام غير متاحة حالياً
        </p>
      </section>
    );
  }

  const { scheduler, latest_bulletin } = data;

  return (
    <section
      aria-labelledby="status-heading"
      className="space-card"
      style={{ padding: '28px 32px' }}
      lang="ar"
      dir="rtl"
    >
      <h2
        id="status-heading"
        lang="ar"
        style={{
          fontSize: '14px',
          fontWeight: 700,
          color: 'var(--text-muted)',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span aria-hidden="true">📡</span>
        حالة النشرة
      </h2>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
          gap: '10px',
        }}
      >
        <InfoItem label="المجدول">
          <span
            style={{
              color: scheduler.enabled ? '#4ade80' : '#7a99bf',
              fontWeight: 600,
            }}
          >
            {scheduler.enabled ? 'مُفعَّل' : 'معطّل'}
          </span>
        </InfoItem>

        <InfoItem label="آخر تشغيل">
          <span style={{ fontSize: '12px' }}>{formatDateTime(scheduler.last_run)}</span>
        </InfoItem>

        <InfoItem label="حالة آخر تشغيل">
          <StatusDot status={scheduler.status} />
        </InfoItem>

        {scheduler.apod_date && (
          <InfoItem label="تاريخ APOD المعالَج">
            {scheduler.apod_date}
          </InfoItem>
        )}

        {scheduler.last_success && (
          <InfoItem label="آخر نجاح">
            <span style={{ fontSize: '12px' }}>{formatDateTime(scheduler.last_success)}</span>
          </InfoItem>
        )}

        {latest_bulletin && (
          <>
            <InfoItem label="آخر نشرة محفوظة">
              {latest_bulletin.apod_date}
            </InfoItem>
            <InfoItem label="حالة النشرة">
              <StatusDot status={latest_bulletin.status} />
            </InfoItem>
          </>
        )}
      </div>
    </section>
  );
}
