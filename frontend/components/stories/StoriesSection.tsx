'use client';

import { useState, useEffect, useCallback } from 'react';
import { fetchStories, APIClientError } from '@/lib/api';
import type { StoryCard } from '@/lib/types';
import { useFavorites } from '@/hooks/useFavorites';

// Debounce helper
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// Temperature classes cycle through cold/cosmic/hot
const TEMP_CLASSES = ['temp-cold', 'temp-cosmic', 'temp-hot', 'temp-cosmic'];

function StoryCardItem({
  story,
  onOpen,
  index,
}: {
  story: StoryCard;
  onOpen: (s: StoryCard) => void;
  index: number;
}) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const fav = isFavorite(story.id);
  const tempClass = TEMP_CLASSES[index % TEMP_CLASSES.length];

  return (
    <article
      className={`space-card ${tempClass}`}
      style={{ padding: 0, overflow: 'hidden', cursor: 'pointer' }}
      onClick={() => onOpen(story)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onOpen(story)}
      aria-label={`فتح قصة: ${story.title}`}
    >
      {/* Image */}
      {story.image_url && story.media_type === 'image' && (
        <div style={{ position: 'relative', aspectRatio: '16/9', overflow: 'hidden' }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={story.image_url}
            alt={story.title}
            loading="lazy"
            style={{ width: '100%', height: '100%', objectFit: 'cover', transition: 'transform 0.4s ease' }}
          />
          <div
            aria-hidden="true"
            style={{
              position: 'absolute',
              inset: 0,
              background: 'linear-gradient(to bottom, transparent 40%, rgba(5,7,18,0.92) 100%)',
            }}
          />
        </div>
      )}
      {(!story.image_url || story.media_type !== 'image') && (
        <div
          style={{
            aspectRatio: '16/9',
            background: `
              radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,217,255,0.06) 0%, transparent 70%),
              rgba(255,255,255,0.025)
            `,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-hidden="true"
        >
          <span style={{ fontSize: '32px', opacity: 0.4 }}>✦</span>
        </div>
      )}

      {/* Content */}
      <div style={{ padding: '14px 16px 16px', position: 'relative' }}>
        {/* Favorite button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleFavorite(story);
          }}
          aria-label={fav ? 'إزالة من المفضلة' : 'إضافة للمحفوظات'}
          style={{
            position: 'absolute',
            top: '12px',
            left: '12px',
            background: fav ? 'rgba(245,200,66,0.12)' : 'transparent',
            border: fav ? '1px solid rgba(245,200,66,0.3)' : 'none',
            borderRadius: '20px',
            padding: fav ? '2px 8px' : '0',
            cursor: 'pointer',
            fontSize: '14px',
            lineHeight: 1,
            color: fav ? 'var(--accent-gold)' : 'var(--text-faint)',
            transition: 'all 0.2s ease',
          }}
        >
          {fav ? '★' : '☆'}
        </button>

        {/* Date */}
        <div
          style={{
            fontSize: '10px',
            color: 'var(--text-faint)',
            marginBottom: '6px',
            direction: 'ltr',
            letterSpacing: '0.04em',
          }}
        >
          {story.date}
        </div>

        {/* Title */}
        <h3
          lang="ar"
          style={{
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--stellar-white)',
            margin: '0 0 7px',
            lineHeight: 1.5,
          }}
        >
          {story.title}
        </h3>

        {/* Summary */}
        <p
          lang="ar"
          style={{
            fontSize: '12px',
            color: 'var(--text-muted)',
            margin: 0,
            lineHeight: 1.7,
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {story.summary}
        </p>

        {story.copyright && (
          <div style={{ fontSize: '10px', color: 'var(--text-faint)', marginTop: '8px', opacity: 0.7 }}>
            © {story.copyright}
          </div>
        )}
      </div>
    </article>
  );
}

function StoryModal({
  story,
  onClose,
}: {
  story: StoryCard;
  onClose: () => void;
}) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const fav = isFavorite(story.id);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={story.title}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'rgba(5,7,18,0.92)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          maxWidth: '720px',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(0,217,255,0.15)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image */}
        {story.image_url && story.media_type === 'image' && (
          <div style={{ maxHeight: '340px', overflow: 'hidden', position: 'relative' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={story.hd_image_url || story.image_url}
              alt={story.title}
              style={{ width: '100%', objectFit: 'cover', display: 'block' }}
            />
            <div aria-hidden="true" style={{
              position: 'absolute',
              bottom: 0, left: 0, right: 0,
              height: '50%',
              background: 'linear-gradient(to top, rgba(5,7,18,0.95), transparent)',
            }} />
          </div>
        )}

        <div style={{ padding: '24px', direction: 'rtl', overflowY: 'auto', maxHeight: '70vh' }} lang="ar">
          {/* Header */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '12px',
            marginBottom: '18px',
          }}>
            <div style={{ flex: 1 }}>
              <div style={{
                fontSize: '10px',
                color: 'var(--text-faint)',
                marginBottom: '6px',
                direction: 'ltr',
                textAlign: 'right',
                letterSpacing: '0.06em',
              }}>
                {story.date} · {story.source}
              </div>
              <h2 style={{
                fontSize: 'clamp(16px, 3vw, 22px)',
                fontWeight: 700,
                color: 'var(--stellar-white)',
                margin: 0,
                lineHeight: 1.4,
              }}>
                {story.title}
              </h2>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              <button
                onClick={() => toggleFavorite(story)}
                aria-label={fav ? 'إزالة من المحفوظات' : 'إضافة للمحفوظات'}
                style={{
                  background: fav ? 'rgba(245,200,66,0.1)' : 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '7px 13px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: fav ? 'var(--accent-gold)' : 'var(--text-faint)',
                  transition: 'all 0.2s',
                }}
              >
                {fav ? '★' : '☆'}
              </button>
              <button
                onClick={onClose}
                aria-label="إغلاق"
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  padding: '7px 13px',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  fontSize: '14px',
                  transition: 'border-color 0.15s',
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Summary */}
          <p style={{
            fontSize: '15px',
            color: 'var(--text-muted)',
            lineHeight: 2,
            margin: '0 0 20px',
          }}>
            {story.summary}
          </p>

          {/* Link to NASA */}
          <a
            href={`https://apod.nasa.gov/apod/ap${story.date.replace(/-/g, '').slice(2)}.html`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              color: 'var(--pulsar-blue)',
              textDecoration: 'none',
              border: '1px solid rgba(0,217,255,0.2)',
              borderRadius: '8px',
              padding: '7px 14px',
              background: 'rgba(0,217,255,0.05)',
            }}
          >
            عرض القصة الكاملة على ناسا ↗
          </a>
        </div>
      </div>
    </div>
  );
}

export default function StoriesSection() {
  const [stories, setStories] = useState<StoryCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedStory, setSelectedStory] = useState<StoryCard | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [endDate, setEndDate] = useState<string | undefined>(undefined);

  const debouncedSearch = useDebounce(search, 300);

  const loadStories = useCallback(async (append = false) => {
    if (!append) setLoading(true);
    else setLoadingMore(true);
    setError(null);

    try {
      let ed = endDate;
      if (append && stories.length > 0) {
        const earliest = stories[stories.length - 1].date;
        const d = new Date(earliest);
        d.setDate(d.getDate() - 1);
        ed = d.toISOString().split('T')[0];
      }
      const data = await fetchStories(6, ed);
      if (append) {
        setStories((prev) => [...prev, ...data.stories]);
      } else {
        setStories(data.stories);
      }
      setEndDate(ed);
    } catch (err) {
      const msg = err instanceof APIClientError ? err.message : 'تعذّر تحميل القصص.';
      setError(msg);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [endDate, stories]);

  useEffect(() => {
    loadStories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Filter by search
  const filtered = debouncedSearch.trim()
    ? stories.filter((s) =>
        s.title.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        s.summary.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        s.date.includes(debouncedSearch)
      )
    : stories;

  return (
    <div lang="ar" dir="rtl">
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{
          fontSize: 'clamp(20px, 3.5vw, 30px)',
          fontWeight: 700,
          color: 'var(--stellar-white)',
          margin: '0 0 6px',
          lineHeight: 1.3,
        }}>
          قصص الكون
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: 0 }}>
          استكشف قصصاً حقيقية من الكون عبر أرشيف ناسا الفلكي
        </p>
      </div>

      {/* Search */}
      <div style={{ marginBottom: '28px', position: 'relative' }}>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="ابحث في قصص الكون…"
          data-testid="stories-search"
          style={{
            width: '100%',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border)',
            borderRadius: '12px',
            padding: '11px 42px 11px 14px',
            color: 'var(--text-primary)',
            fontSize: '14px',
            direction: 'rtl',
            outline: 'none',
            boxSizing: 'border-box',
            transition: 'border-color 0.15s',
          }}
        />
        <span
          style={{
            position: 'absolute',
            right: '14px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-faint)',
            fontSize: '13px',
            pointerEvents: 'none',
          }}
          aria-hidden="true"
        >
          ⌕
        </span>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div
          data-testid="stories-loading"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '20px',
          }}
        >
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-card" style={{ height: '280px' }}>
              <div className="skeleton" style={{ height: '158px', borderRadius: '0' }} />
              <div style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="skeleton" style={{ height: '10px', width: '40%' }} />
                <div className="skeleton" style={{ height: '15px' }} />
                <div className="skeleton" style={{ height: '13px', width: '80%' }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div
          role="alert"
          data-testid="stories-error"
          style={{
            background: 'rgba(248,113,113,0.06)',
            border: '1px solid rgba(248,113,113,0.25)',
            borderRadius: '12px',
            padding: '20px 24px',
            color: 'var(--accent-red)',
            fontSize: '14px',
            textAlign: 'center',
          }}
        >
          <p style={{ margin: '0 0 12px' }}>⚠ {error}</p>
          <button
            onClick={() => loadStories()}
            style={{
              background: 'transparent',
              border: '1px solid var(--accent-red)',
              borderRadius: '8px',
              padding: '7px 18px',
              color: 'var(--accent-red)',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            إعادة المحاولة
          </button>
        </div>
      )}

      {/* No search results */}
      {!loading && !error && filtered.length === 0 && stories.length > 0 && (
        <div
          data-testid="stories-empty"
          style={{
            textAlign: 'center',
            padding: '60px 20px',
            color: 'var(--text-faint)',
          }}
        >
          <p style={{ fontSize: '28px', margin: '0 0 12px', opacity: 0.5 }}>⌕</p>
          <p style={{ margin: 0, fontSize: '15px', color: 'var(--text-muted)' }}>
            لا توجد نتائج لـ «{search}»
          </p>
        </div>
      )}

      {/* Story grid */}
      {!loading && !error && filtered.length > 0 && (
        <>
          <div
            data-testid="stories-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '20px',
            }}
          >
            {filtered.map((story, i) => (
              <StoryCardItem key={story.id} story={story} onOpen={setSelectedStory} index={i} />
            ))}
          </div>

          {/* Load more */}
          {!debouncedSearch.trim() && (
            <div style={{ textAlign: 'center', marginTop: '36px' }}>
              <button
                onClick={() => loadStories(true)}
                disabled={loadingMore}
                className="btn-secondary"
                style={{
                  padding: '11px 32px',
                  fontSize: '14px',
                  opacity: loadingMore ? 0.6 : 1,
                }}
              >
                {loadingMore ? 'جارٍ التحميل…' : 'تحميل المزيد'}
              </button>
            </div>
          )}
        </>
      )}

      {/* Modal */}
      {selectedStory && (
        <StoryModal
          story={selectedStory}
          onClose={() => setSelectedStory(null)}
        />
      )}
    </div>
  );
}
