import FavoritesSection from '@/components/favorites/FavoritesSection';

export const metadata = {
  title: 'مجموعتي الكونية — Space Interpreter',
  description: 'قصصك الفضائية المحفوظة من الكون.',
};

export default function FavoritesPage() {
  return (
    <div style={{ background: 'var(--deep-space)', minHeight: '100vh' }}>
      <div
        style={{
          maxWidth: '820px',
          margin: '0 auto',
          padding: 'clamp(32px, 5vw, 60px) clamp(16px, 4vw, 40px) clamp(40px, 6vw, 80px)',
        }}
      >
        <FavoritesSection />
      </div>
    </div>
  );
}
