import type { SourceData } from '@/lib/types';

interface APODSourceAttributionProps {
  sourceData: SourceData;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr + 'T00:00:00Z').toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: 'UTC',
    });
  } catch {
    return dateStr;
  }
}

export default function APODSourceAttribution({ sourceData }: APODSourceAttributionProps) {
  const { source, date, title, copyright } = sourceData;

  return (
    <div
      lang="ar"
      dir="rtl"
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '8px 16px',
        fontSize: '12px',
        color: 'var(--text-muted)',
      }}
    >
      {/* Source badge */}
      <span
        aria-label={`المصدر: ${source}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: '3px 9px',
          borderRadius: '4px',
          background: 'rgba(74, 158, 255, 0.08)',
          border: '1px solid rgba(74, 158, 255, 0.2)',
          color: 'var(--accent-blue)',
          fontWeight: 600,
          fontSize: '11px',
        }}
      >
        <span aria-hidden="true">🛸</span>
        {source}
      </span>

      {/* Date */}
      <time
        dateTime={date}
        title={date}
        style={{ color: 'var(--text-muted)' }}
      >
        {formatDate(date)}
      </time>

      {/* Original English title */}
      {title && (
        <span
          lang="en"
          dir="ltr"
          title="Original NASA title"
          style={{
            color: 'var(--text-faint)',
            fontStyle: 'italic',
            fontSize: '11px',
          }}
        >
          {title}
        </span>
      )}

      {/* Copyright */}
      {copyright && (
        <span
          title={`حقوق الصورة: ${copyright}`}
          style={{ color: 'var(--text-faint)', fontSize: '11px' }}
        >
          © {copyright}
        </span>
      )}
    </div>
  );
}
