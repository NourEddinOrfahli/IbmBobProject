import type { SpaceStory } from '@/lib/types';

interface ConfidenceBadgeProps {
  confidence: SpaceStory['confidence'];
}

const CONFIG = {
  high: {
    label: 'ثقة عالية',
    bg: 'rgba(245, 200, 66, 0.12)',
    border: 'rgba(245, 200, 66, 0.35)',
    color: '#f5c842',
    dot: '#f5c842',
  },
  medium: {
    label: 'ثقة متوسطة',
    bg: 'rgba(74, 158, 255, 0.1)',
    border: 'rgba(74, 158, 255, 0.3)',
    color: '#4a9eff',
    dot: '#4a9eff',
  },
  low: {
    label: 'ثقة منخفضة',
    bg: 'rgba(251, 146, 60, 0.1)',
    border: 'rgba(251, 146, 60, 0.3)',
    color: '#fb923c',
    dot: '#fb923c',
  },
} as const;

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const key = (confidence in CONFIG ? confidence : 'medium') as keyof typeof CONFIG;
  const c = CONFIG[key];

  return (
    <span
      role="status"
      aria-label={`مستوى الثقة: ${c.label}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '20px',
        background: c.bg,
        border: `1px solid ${c.border}`,
        color: c.color,
        fontSize: '12px',
        fontWeight: 600,
        direction: 'rtl',
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: c.dot,
          display: 'inline-block',
          flexShrink: 0,
        }}
        aria-hidden="true"
      />
      {c.label}
    </span>
  );
}
