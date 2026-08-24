'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

const NAV_ITEMS = [
  { href: '/',            label: 'الرئيسية',         abbr: 'الرئيسية' },
  { href: '/interpreter', label: 'المترجم الفضائي',   abbr: 'المترجم' },
  { href: '/chat',        label: 'المحادثة',          abbr: 'المحادثة' },
  { href: '/stories',     label: 'قصص الكون',         abbr: 'القصص' },
  { href: '/favorites',   label: 'المحفوظات',         abbr: 'المحفوظات' },
];

export default function SpaceNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <nav
        lang="ar"
        dir="rtl"
        aria-label="التنقل الرئيسي"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          background: 'rgba(5, 7, 18, 0.88)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            padding: '0 clamp(16px, 4vw, 32px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: '56px',
          }}
        >
          {/* Brand mark */}
          <Link
            href="/"
            style={{
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              flexShrink: 0,
            }}
          >
            {/* Pulsar icon */}
            <div
              aria-hidden="true"
              style={{
                width: '28px',
                height: '28px',
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {/* Outer ring */}
              <div style={{
                position: 'absolute',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                border: '1px solid rgba(0,217,255,0.25)',
                animation: 'pulsarRing 2.4s ease-in-out infinite',
              }} />
              {/* Core */}
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #00D9FF, #7A2CFF)',
                animation: 'pulsarCore 2.4s ease-in-out infinite',
                boxShadow: '0 0 8px rgba(0,217,255,0.6)',
              }} />
            </div>
            <span
              style={{
                fontSize: '13px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                color: 'var(--stellar-white)',
              }}
            >
              SPACE INTERPRETER
            </span>
          </Link>

          {/* Desktop nav links */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '2px',
            }}
            className="desktop-nav"
          >
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? 'page' : undefined}
                  style={{
                    position: 'relative',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '6px 14px',
                    textDecoration: 'none',
                    fontSize: '13px',
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? 'var(--pulsar-blue)' : 'var(--text-muted)',
                    borderRadius: '8px',
                    transition: 'color 0.15s ease',
                    whiteSpace: 'nowrap',
                    background: isActive ? 'rgba(0,217,255,0.07)' : 'transparent',
                  }}
                >
                  {item.label}
                  {/* Active pulsar dot */}
                  {isActive && (
                    <span
                      aria-hidden="true"
                      style={{
                        position: 'absolute',
                        bottom: '1px',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        width: '4px',
                        height: '4px',
                        borderRadius: '50%',
                        background: 'var(--pulsar-blue)',
                        boxShadow: '0 0 6px rgba(0,217,255,0.8)',
                        animation: 'pulsarCore 2.4s ease-in-out infinite',
                      }}
                    />
                  )}
                </Link>
              );
            })}
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? 'إغلاق القائمة' : 'فتح القائمة'}
            aria-expanded={mobileOpen}
            className="mobile-menu-btn"
            style={{
              display: 'none',
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '6px 10px',
              cursor: 'pointer',
              color: 'var(--text-muted)',
              fontSize: '16px',
              lineHeight: 1,
              flexShrink: 0,
            }}
          >
            {mobileOpen ? '✕' : '☰'}
          </button>
        </div>

        {/* Mobile dropdown */}
        {mobileOpen && (
          <div
            className="mobile-nav"
            lang="ar"
            dir="rtl"
            style={{
              borderTop: '1px solid var(--border)',
              padding: '8px 16px 16px',
            }}
          >
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={isActive ? 'page' : undefined}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    textDecoration: 'none',
                    fontSize: '15px',
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? 'var(--pulsar-blue)' : 'var(--text-muted)',
                    borderRadius: '8px',
                    background: isActive ? 'rgba(0,217,255,0.07)' : 'transparent',
                    marginBottom: '2px',
                  }}
                >
                  <span>{item.label}</span>
                  {isActive && (
                    <span
                      aria-hidden="true"
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'var(--pulsar-blue)',
                        boxShadow: '0 0 6px rgba(0,217,255,0.8)',
                        flexShrink: 0,
                      }}
                    />
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </nav>

      {/* Responsive nav styles */}
      <style>{`
        @media (max-width: 640px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
        @media (min-width: 641px) {
          .mobile-nav { display: none !important; }
          .mobile-menu-btn { display: none !important; }
        }
      `}</style>
    </>
  );
}
