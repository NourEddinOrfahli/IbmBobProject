'use client';

import Link from 'next/link';
import { useDailyNews } from '@/hooks/useDailyNews';
import { useBulletinStatus } from '@/hooks/useBulletinStatus';
import BulletinSkeleton from '@/components/states/BulletinSkeleton';
import BulletinError from '@/components/states/BulletinError';
import BulletinEmpty from '@/components/states/BulletinEmpty';
import MorningBulletinHero from '@/components/dashboard/MorningBulletinHero';
import ScientificStory from '@/components/dashboard/ScientificStory';
import SpaceWeatherSection from '@/components/dashboard/SpaceWeatherSection';
import LiveStatus from '@/components/dashboard/LiveStatus';

// ── Pulsar Hero ────────────────────────────────────────────────────────────
function CosmicHero() {
  return (
    <section
      aria-label="الرئيسية"
      style={{
        position: 'relative',
        padding: 'clamp(56px, 10vw, 100px) 0 clamp(48px, 8vw, 80px)',
        textAlign: 'center',
        overflow: 'hidden',
      }}
    >
      {/* Background nebula radials */}
      <div aria-hidden="true" style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `
          radial-gradient(ellipse 80% 60% at 50% 0%, rgba(0,217,255,0.07) 0%, transparent 60%),
          radial-gradient(ellipse 50% 50% at 20% 60%, rgba(122,44,255,0.05) 0%, transparent 60%),
          radial-gradient(ellipse 40% 40% at 80% 70%, rgba(255,45,154,0.04) 0%, transparent 60%)
        `,
      }} />

      {/* Pulsar icon — large */}
      <div
        aria-hidden="true"
        style={{
          position: 'relative',
          width: '72px',
          height: '72px',
          margin: '0 auto 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Expanding wave rings */}
        {[0, 0.6, 1.2].map((delay, i) => (
          <div key={i} style={{
            position: 'absolute',
            width: '72px',
            height: '72px',
            borderRadius: '50%',
            border: `1px solid rgba(0,217,255,${0.15 - i * 0.04})`,
            animation: `expandWave 2.4s ease-out ${delay}s infinite`,
          }} />
        ))}
        {/* Middle ring */}
        <div style={{
          position: 'absolute',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          border: '1px solid rgba(0,217,255,0.3)',
          animation: 'pulsarRing 2.4s ease-in-out infinite',
        }} />
        {/* Core */}
        <div style={{
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #00D9FF, #7A2CFF)',
          boxShadow: '0 0 16px rgba(0,217,255,0.7), 0 0 32px rgba(122,44,255,0.4)',
          animation: 'pulsarCore 2.4s ease-in-out infinite',
          zIndex: 1,
        }} />
      </div>

      {/* Product name */}
      <div
        style={{
          fontSize: 'clamp(11px, 1.5vw, 13px)',
          fontWeight: 700,
          letterSpacing: '0.18em',
          color: 'var(--pulsar-blue)',
          marginBottom: '14px',
          opacity: 0.9,
        }}
      >
        SPACE INTERPRETER
      </div>

      {/* Main headline */}
      <h1
        lang="ar"
        style={{
          fontSize: 'clamp(28px, 5vw, 52px)',
          fontWeight: 700,
          lineHeight: 1.35,
          marginBottom: '16px',
          color: 'var(--stellar-white)',
          textWrap: 'balance',
        } as React.CSSProperties}
      >
        افهم الكون بطريقة{' '}
        <span className="pulsar-text">مختلفة</span>
      </h1>

      {/* Sub-headline */}
      <p
        lang="ar"
        style={{
          fontSize: 'clamp(14px, 2vw, 17px)',
          color: 'var(--text-muted)',
          lineHeight: 1.8,
          maxWidth: '520px',
          margin: '0 auto 36px',
        }}
      >
        منصة فلكية عربية تستخدم الذكاء الاصطناعي لتحليل صور الفضاء وتفسير الكون
      </p>

      {/* CTA Buttons */}
      <div
        style={{
          display: 'flex',
          gap: '12px',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}
      >
        <Link
          href="/chat"
          className="btn-pulsar"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '13px 28px',
            textDecoration: 'none',
            fontSize: '15px',
            fontWeight: 700,
            color: 'var(--deep-space)',
          }}
        >
          اسأل الذكاء الاصطناعي
        </Link>
        <Link
          href="/interpreter"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 28px',
            textDecoration: 'none',
            fontSize: '15px',
            fontWeight: 600,
            color: 'var(--pulsar-blue)',
            border: '1px solid rgba(0,217,255,0.3)',
            borderRadius: '10px',
            background: 'rgba(0,217,255,0.06)',
            transition: 'background 0.15s ease, border-color 0.15s ease',
          }}
        >
          حلّل صورة فضائية
        </Link>
      </div>
    </section>
  );
}

// ── Quick Actions ─────────────────────────────────────────────────────────
function QuickActions() {
  const actions = [
    { href: '/interpreter', label: 'تحليل صورة',     sub: 'Vision AI',        accent: '--pulsar-blue' },
    { href: '/chat',        label: 'اسأل AI',         sub: 'مساعد فلكي',       accent: '--plasma-violet' },
    { href: '/stories',     label: 'استكشف القصص',   sub: 'أرشيف ناسا',       accent: '--pulsar-pink' },
    { href: '/favorites',   label: 'المحفوظات',      sub: 'مجموعتي',          accent: '--accent-gold' },
  ];

  return (
    <section
      aria-label="وصول سريع"
      lang="ar"
      dir="rtl"
      style={{ marginBottom: '40px' }}
    >
      <h2 style={{
        fontSize: '11px',
        fontWeight: 700,
        letterSpacing: '0.12em',
        color: 'var(--text-faint)',
        textTransform: 'uppercase',
        marginBottom: '14px',
      }}>
        وصول سريع
      </h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '10px',
      }}>
        {actions.map((a) => (
          <Link
            key={a.href}
            href={a.href}
            style={{
              display: 'block',
              padding: '16px 18px',
              textDecoration: 'none',
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid var(--border)`,
              borderRadius: '10px',
              transition: 'border-color 0.15s, background 0.15s',
            }}
          >
            <div style={{
              fontSize: '15px',
              fontWeight: 700,
              color: `var(${a.accent})`,
              marginBottom: '3px',
            }}>
              {a.label}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-faint)' }}>
              {a.sub}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── Section Divider ───────────────────────────────────────────────────────
function SectionLabel({ label, sub }: { label: string; sub?: string }) {
  return (
    <div lang="ar" dir="rtl" style={{ marginBottom: '20px', display: 'flex', alignItems: 'baseline', gap: '10px' }}>
      <span className="section-chip">{label}</span>
      {sub && <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>{sub}</span>}
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────
export default function SpaceDashboard() {
  const { story, loading, error, refetch } = useDailyNews();
  const { status, loading: statusLoading, error: statusError } = useBulletinStatus();

  return (
    <div style={{ background: 'var(--deep-space)', minHeight: '100vh' }}>
      {/* ── Hero section ───────────────────────────────────── */}
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 clamp(16px, 4vw, 32px)' }}>
        <CosmicHero />
      </div>

      {/* ── Main content ──────────────────────────────────── */}
      <div
        style={{
          maxWidth: '960px',
          margin: '0 auto',
          padding: '0 clamp(16px, 4vw, 32px) clamp(40px, 6vw, 80px)',
        }}
      >
        {/* Quick actions */}
        <QuickActions />

        {/* Cosmic Pulse — APOD + daily story */}
        <div style={{ marginBottom: '40px' }}>
          <SectionLabel label="COSMIC PULSE" sub="نبضة اليوم" />

          <div
            role="region"
            aria-label="النشرة الفضائية الصباحية"
            aria-live="polite"
          >
            {loading ? (
              <BulletinSkeleton />
            ) : error ? (
              <BulletinError message={error} onRetry={refetch} />
            ) : !story ? (
              <BulletinEmpty />
            ) : (
              <div className="animate-fade-in">
                <MorningBulletinHero story={story} />
                <ScientificStory story={story} />
              </div>
            )}
          </div>
        </div>

        {/* Space Weather */}
        {!loading && !error && story && (
          <div style={{ marginBottom: '40px' }}>
            <SectionLabel label="SPACE WEATHER" sub="الطقس الفضائي" />
            <SpaceWeatherSection data={story.space_weather} />
          </div>
        )}

        {/* System status */}
        <div style={{ marginBottom: '24px' }}>
          <SectionLabel label="SYSTEM STATUS" sub="حالة النظام" />
          <LiveStatus
            data={status}
            loading={statusLoading}
            error={statusError}
          />
        </div>

        {/* Footer */}
        <footer
          lang="ar"
          dir="rtl"
          style={{
            marginTop: '40px',
            paddingTop: '20px',
            borderTop: '1px solid var(--border)',
            textAlign: 'center',
            fontSize: '12px',
            color: 'var(--text-faint)',
          }}
        >
          <p style={{ margin: 0 }}>
            SPACE INTERPRETER · بُني بالكامل باستخدام IBM Bob · بيانات ناسا المفتوحة
          </p>
        </footer>
      </div>
    </div>
  );
}
