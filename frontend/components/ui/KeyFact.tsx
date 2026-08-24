interface KeyFactProps {
  fact: string;
  index: number;
}

export default function KeyFact({ fact, index }: KeyFactProps) {
  return (
    <li
      lang="ar"
      dir="rtl"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        padding: '10px 14px',
        background: 'rgba(74, 158, 255, 0.04)',
        border: '1px solid rgba(74, 158, 255, 0.12)',
        borderRadius: '8px',
        fontSize: '14px',
        color: 'var(--text-primary)',
        lineHeight: 1.8,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          flexShrink: 0,
          width: 22,
          height: 22,
          borderRadius: '50%',
          background: 'rgba(245, 200, 66, 0.12)',
          border: '1px solid rgba(245, 200, 66, 0.3)',
          color: '#f5c842',
          fontSize: '11px',
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginTop: '2px',
        }}
      >
        {index + 1}
      </span>
      <span>{fact}</span>
    </li>
  );
}
