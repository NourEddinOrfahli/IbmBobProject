import StoriesSection from '@/components/stories/StoriesSection';

export const metadata = {
  title: 'قصص الكون — Space Interpreter',
  description: 'استكشف قصصاً حقيقية من الكون عبر أرشيف ناسا الفلكي بتفسير عربي.',
};

export default function StoriesPage() {
  return (
    <div style={{ background: 'var(--deep-space)', minHeight: '100vh' }}>
      <div
        style={{
          maxWidth: '1140px',
          margin: '0 auto',
          padding: 'clamp(32px, 5vw, 60px) clamp(16px, 4vw, 40px) clamp(40px, 6vw, 80px)',
        }}
      >
        <StoriesSection />
      </div>
    </div>
  );
}
