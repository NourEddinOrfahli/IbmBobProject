import type { SpaceStory } from '@/lib/types';
import KeyFact from '@/components/ui/KeyFact';

interface ScientificStoryProps {
  story: SpaceStory;
}

export default function ScientificStory({ story }: ScientificStoryProps) {
  return (
    <section
      aria-labelledby="science-heading"
      className="space-card"
      style={{ padding: '32px', marginBottom: '24px' }}
      lang="ar"
      dir="rtl"
    >
      {/* ── Scientific explanation ─────────────────────────────── */}
      <div style={{ marginBottom: '32px' }}>
        <h2
          id="science-heading"
          lang="ar"
          style={{
            fontSize: '16px',
            fontWeight: 700,
            color: 'var(--accent-blue)',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span aria-hidden="true">🔬</span>
          التفسير العلمي
        </h2>
        <p
          lang="ar"
          dir="rtl"
          style={{
            fontSize: '15px',
            color: 'var(--text-primary)',
            lineHeight: 2,
            maxWidth: '720px',
          }}
        >
          {story.scientific_explanation}
        </p>
      </div>

      {/* ── Key facts ─────────────────────────────────────────── */}
      {story.key_facts.length > 0 && (
        <div style={{ marginBottom: '32px' }}>
          <h2
            lang="ar"
            style={{
              fontSize: '16px',
              fontWeight: 700,
              color: 'var(--accent-gold)',
              marginBottom: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span aria-hidden="true">✦</span>
            حقائق أساسية
          </h2>
          <ul
            aria-label="الحقائق الأساسية"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: '10px',
              listStyle: 'none',
              padding: 0,
              margin: 0,
            }}
          >
            {story.key_facts.map((fact, i) => (
              <KeyFact key={i} fact={fact} index={i} />
            ))}
          </ul>
        </div>
      )}

      {/* ── Why it matters ────────────────────────────────────── */}
      <div
        style={{
          marginBottom: '32px',
          padding: '20px 24px',
          background: 'rgba(245, 200, 66, 0.04)',
          border: '1px solid rgba(245, 200, 66, 0.15)',
          borderRadius: '10px',
          borderRight: '3px solid var(--accent-gold)',
        }}
      >
        <h2
          lang="ar"
          style={{
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--accent-gold)',
            marginBottom: '10px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span aria-hidden="true">💡</span>
          لماذا يهمنا هذا؟
        </h2>
        <p
          lang="ar"
          dir="rtl"
          style={{
            fontSize: '14px',
            color: 'var(--text-primary)',
            lineHeight: 1.9,
            margin: 0,
          }}
        >
          {story.why_it_matters}
        </p>
      </div>

      {/* ── Narrative story ───────────────────────────────────── */}
      <div>
        <h2
          lang="ar"
          style={{
            fontSize: '16px',
            fontWeight: 700,
            color: 'var(--accent-cyan)',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span aria-hidden="true">📖</span>
          القصة
        </h2>
        <p
          lang="ar"
          dir="rtl"
          style={{
            fontSize: '15px',
            color: 'var(--text-primary)',
            lineHeight: 2.1,
            maxWidth: '720px',
          }}
        >
          {story.story}
        </p>
      </div>
    </section>
  );
}
