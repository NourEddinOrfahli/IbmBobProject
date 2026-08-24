import type { SpaceStory } from '@/lib/types';
import APODImage from '@/components/ui/APODImage';
import APODSourceAttribution from '@/components/ui/APODSourceAttribution';
import ConfidenceBadge from '@/components/ui/ConfidenceBadge';

interface MorningBulletinHeroProps {
  story: SpaceStory;
}

export default function MorningBulletinHero({ story }: MorningBulletinHeroProps) {
  return (
    <section
      className="space-card hero-gradient glow-blue"
      aria-labelledby="hero-headline"
      style={{ marginBottom: '24px', padding: '0' }}
    >
      {/* APOD image — rendered only when available */}
      <APODImage
        sourceData={story.source_data}
        className="hero-image"
      />

      {/* Content area */}
      <div
        lang="ar"
        dir="rtl"
        style={{ padding: '28px 32px 32px' }}
      >
        {/* Section label */}
        <div
          aria-hidden="true"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px',
          }}
        >
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              color: 'var(--accent-blue)',
              textTransform: 'uppercase',
              padding: '3px 10px',
              background: 'rgba(74, 158, 255, 0.08)',
              border: '1px solid rgba(74, 158, 255, 0.2)',
              borderRadius: '4px',
            }}
          >
            النشرة الفضائية الصباحية
          </span>

          {/* Live dot indicator */}
          <span
            aria-label="البيانات حية من ناسا"
            title="البيانات حية من ناسا"
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: '#4ade80',
              display: 'inline-block',
              animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            }}
          />
        </div>

        {/* Arabic headline */}
        <h1
          id="hero-headline"
          lang="ar"
          dir="rtl"
          style={{
            fontSize: 'clamp(22px, 4vw, 32px)',
            fontWeight: 700,
            color: 'var(--text-primary)',
            lineHeight: 1.5,
            marginBottom: '16px',
            textWrap: 'balance',
          } as React.CSSProperties}
        >
          {story.title}
        </h1>

        {/* Summary */}
        <p
          lang="ar"
          dir="rtl"
          style={{
            fontSize: '16px',
            color: 'var(--text-muted)',
            lineHeight: 1.9,
            marginBottom: '24px',
            maxWidth: '680px',
          }}
        >
          {story.summary}
        </p>

        {/* Footer row: attribution + confidence */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border)',
          }}
        >
          <APODSourceAttribution sourceData={story.source_data} />
          <ConfidenceBadge confidence={story.confidence} />
        </div>
      </div>
    </section>
  );
}
