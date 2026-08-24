'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useFavorites } from '@/hooks/useFavorites';
import type { StoryCard } from '@/lib/types';

function FavoriteCard({
  story,
  onRemove,
}: {
  story: StoryCard;
  onRemove: () => void;
}) {
  return (
    <article
      className="space-card"
      style={{ padding: '16px', display: 'flex', gap: '16px', alignItems: 'flex-start' }}
    >
      {/* Thumbnail */}
      {story.image_url && story.media_type === 'image' ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={story.image_url}
          alt={story.title}
          loading="lazy"
          style={{
            width: '84px',
            height: '64px',
            objectFit: 'cover',
            borderRadius: '8px',
            border: '1px solid var(--border)',
            flexShrink: 0,
          }}
        />
      ) : (
        <div
          style={{
            width: '84px',
            height: '64px',
            background: `
              radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,217,255,0.08) 0%, transparent 70%),
              rgba(255,255,255,0.03)
            `,
            borderRadius: '8px',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
          aria-hidden="true"
        >
          <span style={{ fontSize: '18px', opacity: 0.4 }}>✦</span>
        </div>
      )}

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '10px',
          color: 'var(--text-faint)',
          marginBottom: '5px',
          direction: 'ltr',
          letterSpacing: '0.04em',
        }}>
          {story.date} · {story.source}
        </div>
        <h3
          lang="ar"
          style={{
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--stellar-white)',
            margin: '0 0 6px',
            lineHeight: 1.5,
          }}
        >
          {story.title}
        </h3>
        <p
          lang="ar"
          style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            margin: 0,
            lineHeight: 1.65,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {story.summary}
        </p>

        <div style={{ display: 'flex', gap: '10px', marginTop: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <a
            href={`https://apod.nasa.gov/apod/ap${story.date.replace(/-/g, '').slice(2)}.html`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: '11px',
              color: 'var(--pulsar-blue)',
              textDecoration: 'none',
              opacity: 0.85,
            }}
          >
            عرض على ناسا ↗
          </a>

          <button
            onClick={onRemove}
            aria-label="إزالة من المحفوظات"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-faint)',
              fontSize: '11px',
              cursor: 'pointer',
              marginRight: 'auto',
              padding: 0,
              transition: 'color 0.15s',
            }}
          >
            × إزالة
          </button>
        </div>
      </div>
    </article>
  );
}

export default function FavoritesSection() {
  const { favorites, toggleFavorite, clearFavorites } = useFavorites();
  const [confirmClear, setConfirmClear] = useState(false);

  if (favorites.length === 0) {
    return (
      <div lang="ar" dir="rtl">
        <div style={{ marginBottom: '28px' }}>
          <h1 style={{
            fontSize: 'clamp(20px, 3.5vw, 30px)',
            fontWeight: 700,
            color: 'var(--stellar-white)',
            margin: '0 0 6px',
          }}>
            مجموعتي الكونية
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            القصص التي حفظتها من الكون
          </p>
        </div>

        <div
          data-testid="favorites-empty"
          style={{
            textAlign: 'center',
            padding: '80px 20px',
          }}
        >
          {/* Empty state pulsar */}
          <div
            aria-hidden="true"
            style={{
              position: 'relative',
              width: '64px',
              height: '64px',
              margin: '0 auto 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <div style={{
              position: 'absolute',
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              border: '1px solid rgba(245,200,66,0.12)',
              animation: 'pulsarRing 4s ease-in-out infinite',
            }} />
            <span style={{ fontSize: '24px', opacity: 0.5 }}>★</span>
          </div>

          <p style={{ margin: '0 0 8px', fontSize: '16px', fontWeight: 600, color: 'var(--text-muted)' }}>
            لم تحفظ أي قصة بعد
          </p>
          <p style={{ margin: '0 0 24px', fontSize: '13px', color: 'var(--text-faint)' }}>
            استكشف قصص الكون وأضف المفضلة منها إلى مجموعتك
          </p>
          <Link
            href="/stories"
            className="btn-pulsar"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '11px 24px',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 700,
              color: 'var(--deep-space)',
            }}
          >
            استكشف قصص الكون
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div lang="ar" dir="rtl">
      {/* Header */}
      <div
        style={{
          marginBottom: '28px',
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <h1 style={{
            fontSize: 'clamp(20px, 3.5vw, 30px)',
            fontWeight: 700,
            color: 'var(--stellar-white)',
            margin: '0 0 5px',
          }}>
            مجموعتي الكونية
          </h1>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            {favorites.length} {favorites.length === 1 ? 'قصة محفوظة' : 'قصص محفوظة'}
          </p>
        </div>

        {/* Clear all */}
        {!confirmClear ? (
          <button
            onClick={() => setConfirmClear(true)}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '7px 16px',
              color: 'var(--text-faint)',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'border-color 0.15s',
            }}
          >
            مسح الكل
          </button>
        ) : (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => { clearFavorites(); setConfirmClear(false); }}
              style={{
                background: 'rgba(248,113,113,0.08)',
                border: '1px solid rgba(248,113,113,0.3)',
                borderRadius: '8px',
                padding: '7px 16px',
                color: 'var(--accent-red)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              تأكيد المسح
            </button>
            <button
              onClick={() => setConfirmClear(false)}
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '7px 16px',
                color: 'var(--text-muted)',
                fontSize: '12px',
                cursor: 'pointer',
              }}
            >
              إلغاء
            </button>
          </div>
        )}
      </div>

      {/* Favorites list */}
      <div
        data-testid="favorites-list"
        style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
      >
        {favorites.map((story) => (
          <FavoriteCard
            key={story.id}
            story={story}
            onRemove={() => toggleFavorite(story)}
          />
        ))}
      </div>
    </div>
  );
}
