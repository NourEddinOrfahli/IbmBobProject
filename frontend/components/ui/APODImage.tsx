import type { SourceData } from '@/lib/types';

interface APODImageProps {
  sourceData: SourceData;
  className?: string;
}

/**
 * Renders the NASA APOD image when safe to do so.
 *
 * Render rules (strict — never fabricate):
 * - Only renders an <img> when media_type === "image" AND a non-empty image_url exists.
 * - Prefers hd_image_url when available.
 * - When media_type === "video": renders a "video" placeholder card.
 * - When image_url is null/empty: renders a space-gradient fallback.
 */
export default function APODImage({ sourceData, className = '' }: APODImageProps) {
  const { media_type, image_url, hd_image_url, title } = sourceData;

  const isImage = media_type === 'image';
  const displayUrl = isImage
    ? (hd_image_url && hd_image_url.trim() ? hd_image_url : image_url)
    : null;
  const hasImage = isImage && displayUrl && displayUrl.trim().length > 0;

  const sharedStyle: React.CSSProperties = {
    width: '100%',
    borderRadius: '10px',
    overflow: 'hidden',
    position: 'relative',
  };

  if (hasImage) {
    return (
      <div style={sharedStyle} className={className}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={displayUrl!}
          alt={title || 'NASA Astronomy Picture of the Day'}
          style={{
            width: '100%',
            height: 'auto',
            display: 'block',
            borderRadius: '10px',
            maxHeight: '480px',
            objectFit: 'cover',
          }}
          loading="lazy"
        />
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '40%',
            background:
              'linear-gradient(to top, rgba(5,10,20,0.85) 0%, transparent 100%)',
            borderRadius: '0 0 10px 10px',
          }}
        />
      </div>
    );
  }

  if (media_type === 'video') {
    return (
      <div
        className={className}
        role="img"
        aria-label="محتوى الفيديو: صورة اليوم من ناسا عبارة عن فيديو"
        style={{
          ...sharedStyle,
          minHeight: '160px',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '10px',
          padding: '32px 24px',
          color: 'var(--text-muted)',
          fontSize: '14px',
          direction: 'rtl',
        }}
      >
        <span style={{ fontSize: '36px' }} aria-hidden="true">🎬</span>
        <span>محتوى هذا اليوم من ناسا هو فيديو</span>
      </div>
    );
  }

  // No image available — CSS gradient fallback
  return (
    <div
      className={className}
      role="img"
      aria-label="صورة الفضاء غير متاحة حالياً"
      style={{
        ...sharedStyle,
        minHeight: '160px',
        background:
          'radial-gradient(ellipse at 30% 60%, rgba(74,158,255,0.12) 0%, rgba(5,10,20,0.0) 60%), ' +
          'radial-gradient(ellipse at 80% 20%, rgba(245,200,66,0.06) 0%, rgba(5,10,20,0.0) 50%), ' +
          'var(--bg-elevated)',
        border: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-faint)',
        fontSize: '36px',
      }}
    >
      <span aria-hidden="true">🌌</span>
    </div>
  );
}
